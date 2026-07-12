"""AgentGuard firewall — public entry point."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from agentguard.capability.manifest import CapabilityManifest
from agentguard.firewall_ops import FirewallEngine
from agentguard.firewall_types import (
    ACTION_BLOCK,
    ACTION_FORWARD,
    ACTION_QUARANTINE,
    MAX_MESSAGE_BYTES,
    FirewallDecision,
)

F = TypeVar("F", bound=Callable[..., Any])
AF = TypeVar("AF", bound=Callable[..., Awaitable[Any]])
__all__ = [
    "ACTION_BLOCK",
    "ACTION_FORWARD",
    "ACTION_QUARANTINE",
    "AgentGuard",
    "FirewallDecision",
    "MAX_MESSAGE_BYTES",
]

class AgentGuard:
    """Inter-agent security middleware entry point."""

    def __init__(
        self,
        risk_threshold: float = 0.85,
        enable_trust_attestation: bool = True,
        enable_capability_enforcement: bool = True,
        audit_log_path: str = "./audit.jsonl",
        mode: str = "enforce",
        task_objective: str | None = None,
        enable_consistency_check: bool = True,
        consistency_threshold: float = 0.10,
        consistency_ml_risk_floor: float = 0.40,
        model_path: str | None = None,
        require_ml_model: bool = False,
        enable_otel_export: bool = False,
        include_message_preview: bool = True,
        max_message_bytes: int = MAX_MESSAGE_BYTES,
    ) -> None:
        if mode not in ("enforce", "monitor"):
            raise ValueError(f"mode must be 'enforce' or 'monitor', got {mode!r}")
        if max_message_bytes < 1:
            raise ValueError("max_message_bytes must be >= 1")
        eng = FirewallEngine(
            risk_threshold=risk_threshold,
            enable_trust_attestation=enable_trust_attestation,
            enable_capability_enforcement=enable_capability_enforcement,
            enable_consistency_check=enable_consistency_check,
            consistency_ml_risk_floor=consistency_ml_risk_floor,
            consistency_threshold=consistency_threshold,
            mode=mode,
            include_message_preview=include_message_preview,
            max_message_bytes=max_message_bytes,
            audit_log_path=audit_log_path,
            task_objective=task_objective,
            model_path=model_path,
            require_ml_model=require_ml_model,
            enable_otel_export=enable_otel_export,
        )
        self._engine = eng
        self.risk_threshold = eng.risk_threshold
        self.enable_trust_attestation = eng.enable_trust_attestation
        self.enable_capability_enforcement = eng.enable_capability_enforcement
        self.enable_consistency_check = eng.enable_consistency_check
        self.consistency_ml_risk_floor = eng.consistency_ml_risk_floor
        self.mode = eng.mode
        self.include_message_preview = eng.include_message_preview
        self.max_message_bytes = eng.max_message_bytes
        self._logger, self._trust = eng.logger, eng.trust
        self._capabilities, self._rules = eng.capabilities, eng.rules
        self._ml, self._consistency = eng.ml, eng.consistency
        self._mcp_inspector, self._otel = eng.mcp_inspector, eng.otel

    @property
    def is_ml_model_loaded(self) -> bool:
        """Return True when the DeBERTa ONNX scorer is active."""
        return self._ml.is_model_loaded()

    def register_agent(self, agent_id: str, manifest: CapabilityManifest) -> None:
        """Register agent identity, trust keys, and capability manifest."""
        self._engine.register_agent(agent_id, manifest)

    def register_delegated_agent(
        self, parent_agent_id: str, child_manifest: CapabilityManifest
    ) -> CapabilityManifest:
        """Register a sub-agent with monotonic capability attenuation."""
        return self._engine.register_delegated_agent(parent_agent_id, child_manifest)

    def rotate_keys(self) -> None:
        """Rotate ephemeral trust keys for all registered agents."""
        self._trust.rotate_all_keys()

    def sign_payload(self, sender_id: str, payload_bytes: bytes) -> bytes:
        """Sign outgoing payload bytes for inter-agent messages."""
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
        """Run inspection, trust, and size checks on a message."""
        return self._engine.inspect_message(
            sender_id, recipient_id, message, payload_bytes, signature=signature
        )

    def check_tool_call(
        self, agent_id: str, tool_name: str, *, endpoint: str | None = None
    ) -> bool:
        """Validate a tool call; False when blocked in enforce mode."""
        return self._engine.check_tool_call(agent_id, tool_name, endpoint=endpoint)

    def check_data_source(self, agent_id: str, data_source: str) -> bool:
        """Validate data-source access; False when blocked in enforce mode."""
        return self._engine.check_data_source(agent_id, data_source)

    def check_output_tokens(self, agent_id: str, token_count: int) -> bool:
        """Validate output size; False when blocked in enforce mode."""
        return self._engine.check_output_tokens(agent_id, token_count)

    def check_endpoint(self, agent_id: str, endpoint: str) -> bool:
        """Validate an external endpoint; False when blocked in enforce mode."""
        return self._engine.check_endpoint(agent_id, endpoint)

    def wrap_mcp_tool(self, tool_fn: F, agent_id: str) -> F:
        """Wrap a sync MCP tool callable with output inspection."""
        return self._engine.wrap_mcp_tool(tool_fn, self, agent_id)

    def wrap_mcp_tool_async(self, tool_fn: AF, agent_id: str) -> AF:
        """Wrap an async MCP tool callable with output inspection."""
        return self._engine.wrap_mcp_tool_async(tool_fn, self, agent_id)

    def wrap(self, graph: object) -> object:
        """Wrap a LangGraph compiled graph with AgentGuard interception."""
        from agentguard.adapters.langgraph import LangGraphAdapter  # noqa: PLC0415

        return LangGraphAdapter.wrap(self, graph)
