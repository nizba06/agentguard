"""AgentGuard firewall — public entry point."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from agentguard.audit.logger import AppendOnlyLogger
from agentguard.capability.enforcer import CapabilityEnforcer, EnforcementResult
from agentguard.capability.manifest import CapabilityManifest
from agentguard.exceptions import AgentGuardException
from agentguard.inspector.consistency import ConsistencyChecker
from agentguard.inspector.ml_scorer import MLRiskScorer, ModelIntegrityError, ModelNotLoadedWarning
from agentguard.inspector.model_paths import default_model_path, missing_model_files
from agentguard.inspector.rule_filter import InjectionRuleFilter
from agentguard.mcp.output_inspector import MCPOutputInspector
from agentguard.trust.authority import TrustAuthority
from agentguard.trust.signing import verify_signature

TRUST_PASS, TRUST_FAIL, TRUST_SKIP = "PASS", "FAIL", "SKIP"  # noqa: S105
CAP_PASS, CAP_FAIL, CAP_SKIP = "PASS", "FAIL", "SKIP"  # noqa: S105
ACTION_FORWARD, ACTION_QUARANTINE, ACTION_BLOCK = "FORWARD", "QUARANTINE", "BLOCK"

# Hard cap on inter-agent message size (1 MiB) to bound memory/CPU before tokenization.
MAX_MESSAGE_BYTES = 1_048_576

_MODEL_INSTALL_HINT = (
    "Install the ONNX model for enforce-mode ML scoring: "
    "python scripts/download_release_model.py "
    "(or copy artifacts via scripts/install_model.ps1 / install_model.sh). "
    "See README 'Production setup' and docs/source/latency.md for rules-only / monitor modes."
)

F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class FirewallDecision:
    """Outcome of inspecting an inter-agent message."""

    action: str
    risk_score: float
    trust_result: str
    capability_result: str
    failure_reason: str | None


class AgentGuard:
    """Inter-agent security middleware entry point."""

    def __init__(
        self,
        risk_threshold: float = 0.75,
        enable_trust_attestation: bool = True,
        enable_capability_enforcement: bool = True,
        audit_log_path: str = "./audit.jsonl",
        mode: str = "enforce",
        task_objective: str | None = None,
        enable_consistency_check: bool = True,
        consistency_threshold: float = 0.10,
        consistency_ml_risk_floor: float = 0.15,
        model_path: str | None = None,
        require_ml_model: bool = False,
        enable_otel_export: bool = False,
        include_message_preview: bool = True,
        max_message_bytes: int = MAX_MESSAGE_BYTES,
    ) -> None:
        if mode not in ("enforce", "monitor"):
            msg = f"mode must be 'enforce' or 'monitor', got {mode!r}"
            raise ValueError(msg)
        if max_message_bytes < 1:
            msg = "max_message_bytes must be >= 1"
            raise ValueError(msg)

        self.risk_threshold = risk_threshold
        self.enable_trust_attestation = enable_trust_attestation
        self.enable_capability_enforcement = enable_capability_enforcement
        self.enable_consistency_check = enable_consistency_check
        self.consistency_ml_risk_floor = consistency_ml_risk_floor
        self.mode = mode
        self.include_message_preview = include_message_preview
        self.max_message_bytes = max_message_bytes
        self._logger = AppendOnlyLogger(audit_log_path)
        self._trust = TrustAuthority()
        self._capabilities = CapabilityEnforcer()
        self._rules = InjectionRuleFilter()
        self._ml = MLRiskScorer()
        self._consistency = ConsistencyChecker(threshold=consistency_threshold)
        self._mcp_inspector = MCPOutputInspector(self._rules, self._ml, risk_threshold)
        if task_objective:
            self._consistency.set_task_objective(task_objective)
        resolved = model_path or (
            str(default_model_path()) if default_model_path().exists() else None
        )
        if resolved:
            try:
                self._ml.load_model(resolved)
            except FileNotFoundError:
                missing = ", ".join(missing_model_files())
                warnings.warn(
                    f"ML model not loaded. Missing under agentguard/models/: {missing}. "
                    f"{_MODEL_INSTALL_HINT}",
                    ModelNotLoadedWarning,
                    stacklevel=2,
                )
            except ModelIntegrityError as exc:
                raise AgentGuardException(
                    action=ACTION_BLOCK,
                    sender_id="",
                    recipient_id="",
                    risk_score=0.0,
                    trust_result=TRUST_SKIP,
                    capability_result=CAP_SKIP,
                    failure_reason=str(exc),
                ) from exc
        elif require_ml_model:
            missing = ", ".join(missing_model_files())
            msg = (
                f"require_ml_model=True but no model found. Missing: {missing}. "
                f"{_MODEL_INSTALL_HINT}"
            )
            raise AgentGuardException(
                action=ACTION_BLOCK,
                sender_id="",
                recipient_id="",
                risk_score=0.0,
                trust_result=TRUST_SKIP,
                capability_result=CAP_SKIP,
                failure_reason=msg,
            )

        self._otel: Any | None = None
        if enable_otel_export:
            from agentguard.audit.otel import (  # noqa: PLC0415
                AuditOtelExporter,
                create_otel_exporter_if_configured,
            )

            self._otel = create_otel_exporter_if_configured() or AuditOtelExporter()

    @property
    def is_ml_model_loaded(self) -> bool:
        """Return True when the DeBERTa ONNX scorer is active."""
        return self._ml.is_model_loaded()

    def register_agent(self, agent_id: str, manifest: CapabilityManifest) -> None:
        """Register agent identity, trust keys, and capability manifest."""
        if manifest.agent_id != agent_id:
            raise ValueError(f"Manifest agent_id '{manifest.agent_id}' != '{agent_id}'")
        if self.enable_trust_attestation:
            self._trust.register_agent(agent_id)
        if self.enable_capability_enforcement:
            self._capabilities.register_agent(agent_id, manifest)

    def register_delegated_agent(
        self,
        parent_agent_id: str,
        child_manifest: CapabilityManifest,
    ) -> CapabilityManifest:
        """Register a sub-agent with monotonic capability attenuation."""
        if self.enable_trust_attestation:
            self._trust.register_agent(child_manifest.agent_id)
        if not self.enable_capability_enforcement:
            return child_manifest
        return self._capabilities.register_delegated_agent(parent_agent_id, child_manifest)

    def rotate_keys(self) -> None:
        """Rotate ephemeral trust keys for all registered agents."""
        self._trust.rotate_all_keys()

    def sign_payload(self, sender_id: str, payload_bytes: bytes) -> bytes:
        """Sign outgoing payload bytes for attachment to inter-agent messages."""
        return self._trust.sign_for_agent(sender_id, payload_bytes)

    def inspect_message(
        self,
        sender_id: str,
        recipient_id: str,
        message: str,
        payload_bytes: bytes,
        *,
        signature: bytes | None = None,
    ) -> FirewallDecision:
        """Run inspection, trust, and size checks on a message.

        Capability tool/endpoint checks run via ``check_tool_call`` and related
        methods at the tool layer; message inspection reports capability as SKIP.
        """
        trust_result, cap_result, failure = TRUST_SKIP, CAP_SKIP, None
        action = ACTION_FORWARD

        if len(payload_bytes) > self.max_message_bytes:
            failure = (
                f"message_size: {len(payload_bytes)} bytes exceeds "
                f"max_message_bytes={self.max_message_bytes}"
            )
            action = ACTION_BLOCK
            return self._finalize_decision(
                sender_id=sender_id,
                recipient_id=recipient_id,
                risk=1.0,
                trust_result=trust_result,
                cap_result=cap_result,
                action=action,
                failure=failure,
                message=message,
                payload_bytes=payload_bytes,
            )

        rule = self._rules.scan(message)
        ml_score = self._ml.score(message)
        if not self._ml.is_model_loaded():
            ml_score = 0.0
        risk = max(ml_score, 0.9 if rule.flagged else 0.0)
        if rule.flagged:
            failure, action = f"rule_filter: {rule.matched_rules[0]}", ACTION_QUARANTINE
        elif risk >= self.risk_threshold:
            failure, action = f"ml_scorer: risk={risk:.3f}", ACTION_QUARANTINE
        elif self.enable_consistency_check:
            check = self._consistency.check(message)
            risk_floor = (
                self.consistency_ml_risk_floor if self._ml.is_model_loaded() else 1.0
            )
            if not check.consistent and risk >= risk_floor:
                failure = f"consistency: similarity={check.similarity_score:.3f}"
                action = ACTION_QUARANTINE

        if self.enable_trust_attestation:
            trust_result, trust_failure, trust_action = self._evaluate_trust(
                sender_id,
                payload_bytes,
                signature,
            )
            if trust_action == ACTION_BLOCK:
                failure = trust_failure
                action = ACTION_BLOCK

        return self._finalize_decision(
            sender_id=sender_id,
            recipient_id=recipient_id,
            risk=risk,
            trust_result=trust_result,
            cap_result=cap_result,
            action=action,
            failure=failure,
            message=message,
            payload_bytes=payload_bytes,
        )

    def _evaluate_trust(
        self,
        sender_id: str,
        payload_bytes: bytes,
        signature: bytes | None,
    ) -> tuple[str, str | None, str]:
        """Return (trust_result, failure_reason, action) for attestation."""
        if signature is None:
            return TRUST_FAIL, "trust: missing signature", ACTION_BLOCK
        try:
            public_key = self._trust.get_public_key(sender_id)
        except KeyError:
            return TRUST_FAIL, f"trust: unregistered sender '{sender_id}'", ACTION_BLOCK
        if not verify_signature(payload_bytes, signature, public_key):
            return TRUST_FAIL, "trust: invalid signature", ACTION_BLOCK
        return TRUST_PASS, None, ACTION_FORWARD

    def _finalize_decision(
        self,
        *,
        sender_id: str,
        recipient_id: str,
        risk: float,
        trust_result: str,
        cap_result: str,
        action: str,
        failure: str | None,
        message: str,
        payload_bytes: bytes,
    ) -> FirewallDecision:
        if self.mode == "monitor" and action != ACTION_BLOCK:
            action = ACTION_FORWARD
        preview = message[:120] if self.include_message_preview and message else None
        self._logger.write_entry(
            sender_id=sender_id,
            recipient_id=recipient_id,
            risk_score=risk,
            trust_result=trust_result,
            capability_result=cap_result,
            action=action,
            failure_reason=failure,
            message_preview=preview,
            payload_bytes=payload_bytes,
        )
        if self._otel is not None and self._logger.entries:
            self._otel.export_entry(self._logger.entries[-1])
        return FirewallDecision(action, risk, trust_result, cap_result, failure)

    def _apply_capability_result(
        self,
        agent_id: str,
        tool_name: str,
        result: EnforcementResult,
        *,
        detail: str | None = None,
    ) -> bool:
        """Log a capability check and return whether the call is allowed."""
        allowed = result.allowed or self.mode == "monitor"
        preview = f"tool:{tool_name}"
        if detail:
            preview = f"{preview}:{detail}"
        self._logger.write_entry(
            sender_id=agent_id,
            recipient_id="tool_layer",
            risk_score=None,
            trust_result=TRUST_SKIP,
            capability_result=CAP_PASS if result.allowed else CAP_FAIL,
            action=ACTION_FORWARD if allowed else ACTION_BLOCK,
            failure_reason=None if result.allowed else result.reason,
            message_preview=preview if self.include_message_preview else None,
            payload_bytes=preview.encode(),
        )
        return allowed if self.mode == "enforce" else True

    def check_tool_call(
        self,
        agent_id: str,
        tool_name: str,
        *,
        endpoint: str | None = None,
    ) -> bool:
        """Validate a tool call; returns False when blocked in enforce mode."""
        if not self.enable_capability_enforcement:
            return True
        result = self._capabilities.check_tool_call(agent_id, tool_name, endpoint=endpoint)
        return self._apply_capability_result(
            agent_id,
            tool_name,
            result,
            detail=endpoint,
        )

    def check_data_source(self, agent_id: str, data_source: str) -> bool:
        """Validate data-source access; returns False when blocked in enforce mode."""
        if not self.enable_capability_enforcement:
            return True
        result = self._capabilities.check_data_source(agent_id, data_source)
        return self._apply_capability_result(agent_id, f"data:{data_source}", result)

    def check_output_tokens(self, agent_id: str, token_count: int) -> bool:
        """Validate output size; returns False when blocked in enforce mode."""
        if not self.enable_capability_enforcement:
            return True
        result = self._capabilities.check_output_tokens(agent_id, token_count)
        return self._apply_capability_result(
            agent_id,
            "output_tokens",
            result,
            detail=str(token_count),
        )

    def check_endpoint(self, agent_id: str, endpoint: str) -> bool:
        """Validate an external endpoint; returns False when blocked in enforce mode."""
        if not self.enable_capability_enforcement:
            return True
        result = self._capabilities.check_endpoint(agent_id, endpoint)
        return self._apply_capability_result(agent_id, "endpoint", result, detail=endpoint)

    def wrap_mcp_tool(self, tool_fn: F, agent_id: str) -> F:
        """Wrap an MCP tool callable with output inspection."""
        return self._mcp_inspector.wrap_tool(tool_fn, self, agent_id)

    def wrap(self, graph: object) -> object:
        """Wrap a LangGraph compiled graph with AgentGuard interception."""
        from agentguard.adapters.langgraph import LangGraphAdapter  # noqa: PLC0415

        return LangGraphAdapter.wrap(self, graph)
