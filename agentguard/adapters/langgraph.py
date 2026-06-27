"""LangGraph StateGraph adapter for AgentGuard."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

from agentguard.exceptions import AgentGuardException
from agentguard.firewall import ACTION_BLOCK, ACTION_QUARANTINE, AgentGuard


class LangGraphAdapter:
    """Wraps LangGraph graphs to intercept inter-node messages."""

    @staticmethod
    def wrap(guard: AgentGuard, graph: Any) -> Any:
        """Wrap a compiled LangGraph graph with message inspection.

        Args:
            guard: Configured AgentGuard instance.
            graph: Compiled LangGraph graph with a ``nodes`` mapping.

        Returns:
            The same graph with guarded node callables.

        Raises:
            TypeError: If the graph does not expose a nodes mapping.
        """
        if not hasattr(graph, "nodes"):
            msg = "Expected a compiled LangGraph graph with a nodes mapping"
            raise TypeError(msg)

        wrapped: dict[str, Any] = {}
        for name, spec in dict(graph.nodes).items():
            runnable = LangGraphAdapter._extract_runnable(spec)
            wrapped[name] = LangGraphAdapter._guard_node(guard, name, runnable, spec)
        graph.nodes = wrapped
        return graph

    @staticmethod
    def _extract_runnable(node_spec: Any) -> Callable[..., Any]:
        if callable(node_spec):
            return cast(Callable[..., Any], node_spec)
        if hasattr(node_spec, "invoke"):
            return cast(Callable[..., Any], node_spec.invoke)
        msg = f"Unsupported node spec: {type(node_spec)!r}"
        raise TypeError(msg)

    @staticmethod
    def _guard_node(
        guard: AgentGuard,
        node_name: str,
        runnable: Callable[..., Any],
        node_spec: Any,
    ) -> Any:
        def guarded(state: dict[str, Any], *args: object, **kwargs: object) -> dict[str, Any]:
            result = runnable(state, *args, **kwargs) if args or kwargs else runnable(state)
            if not isinstance(result, dict):
                return cast(dict[str, Any], result)
            messages = result.get("messages")
            if not isinstance(messages, list):
                return result

            for msg in messages:
                parsed = LangGraphAdapter._parse_message(msg, node_name)
                if parsed is None:
                    continue
                sender, recipient, text, payload, signature = parsed
                decision = guard.inspect_message(
                    sender, recipient, text, payload, signature=signature,
                )
                if decision.action in (ACTION_QUARANTINE, ACTION_BLOCK):
                    raise AgentGuardException(
                        action=decision.action,
                        sender_id=sender,
                        recipient_id=recipient,
                        risk_score=decision.risk_score,
                        trust_result=decision.trust_result,
                        capability_result=decision.capability_result,
                        failure_reason=decision.failure_reason,
                    )
            return result

        if callable(node_spec):
            return guarded
        if hasattr(node_spec, "invoke"):
            node_spec.invoke = guarded
        return node_spec

    @staticmethod
    def _parse_message(
        message: Any,
        default_sender: str,
    ) -> tuple[str, str, str, bytes, bytes | None] | None:
        if isinstance(message, dict):
            content = message.get("content") or message.get("payload")
            if content is None:
                return None
            sender = str(message.get("sender_id", default_sender))
            recipient = str(message.get("recipient_id", "downstream"))
            text = str(content)
            payload = text.encode("utf-8")
            sig_raw = message.get("signature")
            signature = bytes(sig_raw) if isinstance(sig_raw, (bytes, bytearray)) else None
            return sender, recipient, text, payload, signature
        if isinstance(message, str):
            return default_sender, "downstream", message, message.encode("utf-8"), None
        return None
