"""AgentGuard firewall — public entry point."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from agentguard.audit.logger import AppendOnlyLogger
from agentguard.capability.enforcer import CapabilityEnforcer
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
        model_path: str | None = None,
        require_ml_model: bool = False,
    ) -> None:
        self.risk_threshold = risk_threshold
        self.enable_trust_attestation = enable_trust_attestation
        self.enable_capability_enforcement = enable_capability_enforcement
        self.mode = mode
        self._logger = AppendOnlyLogger(audit_log_path)
        self._trust = TrustAuthority()
        self._capabilities = CapabilityEnforcer()
        self._rules = InjectionRuleFilter()
        self._ml = MLRiskScorer()
        self._consistency = ConsistencyChecker()
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
                    f"ML model not loaded. Missing under agentguard/models/: {missing}",
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
            msg = f"require_ml_model=True but no model found. Missing: {missing}"
            raise AgentGuardException(
                action=ACTION_BLOCK,
                sender_id="",
                recipient_id="",
                risk_score=0.0,
                trust_result=TRUST_SKIP,
                capability_result=CAP_SKIP,
                failure_reason=msg,
            )

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
        """Run inspection, trust, and capability checks on a message."""
        trust_result, cap_result, failure = TRUST_SKIP, CAP_SKIP, None
        action = ACTION_FORWARD
        rule = self._rules.scan(message)
        risk = max(self._ml.score(message), 0.9 if rule.flagged else 0.0)
        if rule.flagged:
            failure, action = f"rule_filter: {rule.matched_rules[0]}", ACTION_QUARANTINE
        elif risk >= self.risk_threshold:
            failure, action = f"ml_scorer: risk={risk:.3f}", ACTION_QUARANTINE
        else:
            check = self._consistency.check(message)
            if not check.consistent:
                failure = f"consistency: similarity={check.similarity_score:.3f}"
                action = ACTION_QUARANTINE
        if self.enable_trust_attestation:
            if signature is None or not verify_signature(
                payload_bytes, signature, self._trust.get_public_key(sender_id),
            ):
                trust_result = TRUST_FAIL
                failure = failure or "trust: missing signature"
                action = ACTION_BLOCK
                if signature is not None:
                    failure, action = "trust: invalid signature", ACTION_BLOCK
            else:
                trust_result = TRUST_PASS
        if self.mode == "monitor" and action != ACTION_BLOCK:
            action = ACTION_FORWARD
        self._logger.write_entry(
            sender_id=sender_id, recipient_id=recipient_id, risk_score=risk,
            trust_result=trust_result, capability_result=cap_result, action=action,
            failure_reason=failure, message_preview=message[:120] if message else None,
            payload_bytes=payload_bytes,
        )
        return FirewallDecision(action, risk, trust_result, cap_result, failure)

    def check_tool_call(self, agent_id: str, tool_name: str) -> bool:
        """Validate a tool call; returns False when blocked in enforce mode."""
        if not self.enable_capability_enforcement:
            return True
        result = self._capabilities.check_tool_call(agent_id, tool_name)
        allowed = result.allowed or self.mode == "monitor"
        self._logger.write_entry(
            sender_id=agent_id, recipient_id="tool_layer", risk_score=None,
            trust_result=TRUST_SKIP, capability_result=CAP_PASS if result.allowed else CAP_FAIL,
            action=ACTION_FORWARD if allowed else ACTION_BLOCK,
            failure_reason=None if result.allowed else result.reason,
            message_preview=f"tool:{tool_name}", payload_bytes=f"tool:{tool_name}".encode(),
        )
        return allowed if self.mode == "enforce" else True

    def wrap_mcp_tool(self, tool_fn: F, agent_id: str) -> F:
        """Wrap an MCP tool callable with output inspection."""
        return self._mcp_inspector.wrap_tool(tool_fn, self, agent_id)

    def wrap(self, graph: object) -> object:
        """Wrap a LangGraph compiled graph with AgentGuard interception."""
        from agentguard.adapters.langgraph import LangGraphAdapter  # noqa: PLC0415

        return LangGraphAdapter.wrap(self, graph)
