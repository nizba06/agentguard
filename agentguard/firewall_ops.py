"""Internal firewall engine — inspection, trust, and capability helpers."""

from __future__ import annotations

import warnings
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from agentguard.audit.logger import AppendOnlyLogger
from agentguard.capability.enforcer import CapabilityEnforcer, EnforcementResult
from agentguard.capability.manifest import CapabilityManifest
from agentguard.exceptions import AgentGuardException
from agentguard.firewall_types import (
    _MODEL_INSTALL_HINT,
    ACTION_BLOCK,
    ACTION_FORWARD,
    ACTION_QUARANTINE,
    CAP_FAIL,
    CAP_PASS,
    CAP_SKIP,
    TRUST_FAIL,
    TRUST_PASS,
    TRUST_SKIP,
    FirewallDecision,
)
from agentguard.inspector.consistency import ConsistencyChecker
from agentguard.inspector.ml_scorer import MLRiskScorer, ModelIntegrityError, ModelNotLoadedWarning
from agentguard.inspector.model_paths import default_model_path, missing_model_files
from agentguard.inspector.rule_filter import InjectionRuleFilter
from agentguard.mcp.output_inspector import MCPOutputInspector
from agentguard.trust.authority import TrustAuthority
from agentguard.trust.signing import verify_signature

F = TypeVar("F", bound=Callable[..., Any])
AF = TypeVar("AF", bound=Callable[..., Awaitable[Any]])


class FirewallEngine:
    """Security pipeline used by :class:`~agentguard.firewall.AgentGuard`."""

    def __init__(
        self,
        *,
        risk_threshold: float,
        enable_trust_attestation: bool,
        enable_capability_enforcement: bool,
        enable_consistency_check: bool,
        consistency_ml_risk_floor: float,
        consistency_threshold: float,
        mode: str,
        include_message_preview: bool,
        max_message_bytes: int,
        audit_log_path: str,
        task_objective: str | None,
        model_path: str | None,
        require_ml_model: bool,
        enable_otel_export: bool,
    ) -> None:
        self.risk_threshold = risk_threshold
        self.enable_trust_attestation = enable_trust_attestation
        self.enable_capability_enforcement = enable_capability_enforcement
        self.enable_consistency_check = enable_consistency_check
        self.consistency_ml_risk_floor = consistency_ml_risk_floor
        self.mode = mode
        self.include_message_preview = include_message_preview
        self.max_message_bytes = max_message_bytes
        self.logger = AppendOnlyLogger(audit_log_path)
        self.trust = TrustAuthority()
        self.capabilities = CapabilityEnforcer()
        self.rules = InjectionRuleFilter()
        self.ml = MLRiskScorer()
        self.consistency = ConsistencyChecker(threshold=consistency_threshold)
        self.mcp_inspector = MCPOutputInspector(self.rules, self.ml, risk_threshold)
        if task_objective:
            self.consistency.set_task_objective(task_objective)
        self._load_ml_model(model_path, require_ml_model)
        self.otel: Any | None = None
        if enable_otel_export:
            from agentguard.audit.otel import (  # noqa: PLC0415
                AuditOtelExporter,
                create_otel_exporter_if_configured,
            )

            self.otel = create_otel_exporter_if_configured() or AuditOtelExporter()

    def _load_ml_model(self, model_path: str | None, require_ml_model: bool) -> None:
        resolved = model_path or (
            str(default_model_path()) if default_model_path().exists() else None
        )
        if resolved:
            try:
                self.ml.load_model(resolved)
            except FileNotFoundError:
                missing = ", ".join(missing_model_files())
                warnings.warn(
                    f"ML model not loaded. Missing under agentguard/models/: {missing}. "
                    f"{_MODEL_INSTALL_HINT}",
                    ModelNotLoadedWarning,
                    stacklevel=4,
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
            raise AgentGuardException(
                action=ACTION_BLOCK,
                sender_id="",
                recipient_id="",
                risk_score=0.0,
                trust_result=TRUST_SKIP,
                capability_result=CAP_SKIP,
                failure_reason=(
                    f"require_ml_model=True but no model found. Missing: {missing}. "
                    f"{_MODEL_INSTALL_HINT}"
                ),
            )

    def register_agent(self, agent_id: str, manifest: CapabilityManifest) -> None:
        if manifest.agent_id != agent_id:
            raise ValueError(f"Manifest agent_id '{manifest.agent_id}' != '{agent_id}'")
        if self.enable_trust_attestation:
            self.trust.register_agent(agent_id)
        if self.enable_capability_enforcement:
            self.capabilities.register_agent(agent_id, manifest)

    def register_delegated_agent(
        self,
        parent_agent_id: str,
        child_manifest: CapabilityManifest,
    ) -> CapabilityManifest:
        if self.enable_trust_attestation:
            self.trust.register_agent(child_manifest.agent_id)
        if not self.enable_capability_enforcement:
            return child_manifest
        return self.capabilities.register_delegated_agent(parent_agent_id, child_manifest)

    def evaluate_trust(
        self,
        sender_id: str,
        payload_bytes: bytes,
        signature: bytes | None,
    ) -> tuple[str, str | None, str]:
        if signature is None:
            return TRUST_FAIL, "trust: missing signature", ACTION_BLOCK
        try:
            public_key = self.trust.get_public_key(sender_id)
        except KeyError:
            return TRUST_FAIL, f"trust: unregistered sender '{sender_id}'", ACTION_BLOCK
        if not verify_signature(payload_bytes, signature, public_key):
            return TRUST_FAIL, "trust: invalid signature", ACTION_BLOCK
        return TRUST_PASS, None, ACTION_FORWARD

    def finalize(
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
        self.logger.write_entry(
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
        if self.otel is not None and self.logger.entries:
            self.otel.export_entry(self.logger.entries[-1])
        return FirewallDecision(action, risk, trust_result, cap_result, failure)

    def apply_capability(
        self,
        agent_id: str,
        tool_name: str,
        result: EnforcementResult,
        *,
        detail: str | None = None,
    ) -> bool:
        allowed = result.allowed or self.mode == "monitor"
        preview = f"tool:{tool_name}"
        if detail:
            preview = f"{preview}:{detail}"
        self.logger.write_entry(
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

    def inspect_message(
        self,
        sender_id: str,
        recipient_id: str,
        message: str,
        payload_bytes: bytes,
        *,
        signature: bytes | None = None,
    ) -> FirewallDecision:
        trust_result, cap_result, failure = TRUST_SKIP, CAP_SKIP, None
        action = ACTION_FORWARD
        if len(payload_bytes) > self.max_message_bytes:
            return self.finalize(
                sender_id=sender_id,
                recipient_id=recipient_id,
                risk=1.0,
                trust_result=trust_result,
                cap_result=cap_result,
                action=ACTION_BLOCK,
                failure=(
                    f"message_size: {len(payload_bytes)} bytes exceeds "
                    f"max_message_bytes={self.max_message_bytes}"
                ),
                message=message,
                payload_bytes=payload_bytes,
            )
        rule = self.rules.scan(message)
        # Rules-only / unloaded model: skip score() — no ModelNotLoadedWarning spam.
        ml_score = self.ml.score(message) if self.ml.is_model_loaded() else 0.0
        risk = max(ml_score, 0.9 if rule.flagged else 0.0)
        if rule.flagged:
            failure, action = f"rule_filter: {rule.matched_rules[0]}", ACTION_QUARANTINE
        elif risk >= self.risk_threshold:
            failure, action = f"ml_scorer: risk={risk:.3f}", ACTION_QUARANTINE
        elif self.enable_consistency_check:
            check = self.consistency.check(message)
            risk_floor = (
                self.consistency_ml_risk_floor if self.ml.is_model_loaded() else 1.0
            )
            if not check.consistent and risk >= risk_floor:
                failure = f"consistency: similarity={check.similarity_score:.3f}"
                action = ACTION_QUARANTINE
        if self.enable_trust_attestation:
            trust_result, trust_failure, trust_action = self.evaluate_trust(
                sender_id, payload_bytes, signature
            )
            if trust_action == ACTION_BLOCK:
                failure, action = trust_failure, ACTION_BLOCK
        return self.finalize(
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

    def check_tool_call(
        self, agent_id: str, tool_name: str, *, endpoint: str | None = None
    ) -> bool:
        if not self.enable_capability_enforcement:
            return True
        result = self.capabilities.check_tool_call(agent_id, tool_name, endpoint=endpoint)
        return self.apply_capability(agent_id, tool_name, result, detail=endpoint)

    def check_data_source(self, agent_id: str, data_source: str) -> bool:
        if not self.enable_capability_enforcement:
            return True
        result = self.capabilities.check_data_source(agent_id, data_source)
        return self.apply_capability(agent_id, f"data:{data_source}", result)

    def check_output_tokens(self, agent_id: str, token_count: int) -> bool:
        if not self.enable_capability_enforcement:
            return True
        result = self.capabilities.check_output_tokens(agent_id, token_count)
        return self.apply_capability(agent_id, "output_tokens", result, detail=str(token_count))

    def check_endpoint(self, agent_id: str, endpoint: str) -> bool:
        if not self.enable_capability_enforcement:
            return True
        result = self.capabilities.check_endpoint(agent_id, endpoint)
        return self.apply_capability(agent_id, "endpoint", result, detail=endpoint)

    def wrap_mcp_tool(self, tool_fn: F, guard: Any, agent_id: str) -> F:
        return self.mcp_inspector.wrap_tool(tool_fn, guard, agent_id)

    def wrap_mcp_tool_async(self, tool_fn: AF, guard: Any, agent_id: str) -> AF:
        return self.mcp_inspector.wrap_tool_async(tool_fn, guard, agent_id)
