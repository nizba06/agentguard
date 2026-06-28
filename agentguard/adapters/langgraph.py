"""LangGraph StateGraph adapter for AgentGuard."""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import Any, cast

from agentguard.exceptions import AgentGuardException
from agentguard.firewall import ACTION_BLOCK, ACTION_QUARANTINE, AgentGuard


class LangGraphAdapter:
    """Wraps LangGraph graphs to intercept inter-node messages."""

    @staticmethod
    def wrap(guard: AgentGuard, graph: Any) -> Any:
        """Wrap a compiled LangGraph graph with message inspection.

        LangGraph 1.x executes nodes via ``PregelNode.bound.func``, not
        ``PregelNode.invoke`` or a replaceable ``nodes`` dict. We patch
        node specs in place so the compiled graph's internal references
        stay valid.

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

        for name, spec in list(graph.nodes.items()):
            LangGraphAdapter._apply_guard(guard, name, spec, graph)
        return graph

    @staticmethod
    def _apply_guard(
        guard: AgentGuard,
        node_name: str,
        spec: Any,
        graph: Any,
    ) -> None:
        """Patch a single node spec in place (PregelNode, callable, or invoke)."""
        bound = getattr(spec, "bound", None)
        if bound is not None:
            if hasattr(bound, "func") and callable(bound.func):
                bound.func = LangGraphAdapter._wrap_runnable(guard, node_name, bound.func)
                return
            if hasattr(bound, "afunc") and callable(bound.afunc):
                bound.afunc = LangGraphAdapter._wrap_runnable_async(guard, node_name, bound.afunc)
                return

        if callable(spec):
            graph.nodes[node_name] = LangGraphAdapter._wrap_runnable(guard, node_name, spec)
            return

        if hasattr(spec, "invoke"):
            spec.invoke = LangGraphAdapter._wrap_runnable(guard, node_name, spec.invoke)
            return

        msg = f"Unsupported LangGraph node spec for {node_name!r}: {type(spec)!r}"
        raise TypeError(msg)

    @staticmethod
    def _wrap_runnable(
        guard: AgentGuard,
        node_name: str,
        runnable: Callable[..., Any],
    ) -> Callable[..., Any]:
        @functools.wraps(runnable)
        def guarded(state: dict[str, Any], *args: object, **kwargs: object) -> dict[str, Any]:
            if args or kwargs:
                result = runnable(state, *args, **kwargs)
            else:
                result = runnable(state)
            return LangGraphAdapter._inspect_node_output(guard, node_name, result)

        return guarded

    @staticmethod
    def _wrap_runnable_async(
        guard: AgentGuard,
        node_name: str,
        runnable: Callable[..., Awaitable[Any]],
    ) -> Callable[..., Awaitable[Any]]:
        @functools.wraps(runnable)
        async def guarded(state: dict[str, Any], *args: object, **kwargs: object) -> dict[str, Any]:
            if args or kwargs:
                result = await runnable(state, *args, **kwargs)
            else:
                result = await runnable(state)
            return LangGraphAdapter._inspect_node_output(guard, node_name, result)

        return guarded

    @staticmethod
    def _inspect_node_output(
        guard: AgentGuard,
        node_name: str,
        result: Any,
    ) -> dict[str, Any]:
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
                sender,
                recipient,
                text,
                payload,
                signature=signature,
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
