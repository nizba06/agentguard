"""AutoGen GroupChat adapter for AgentGuard."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agentguard.exceptions import AgentGuardException
from agentguard.firewall import ACTION_BLOCK, ACTION_QUARANTINE, AgentGuard


class AutoGenAdapter:
    """Wraps AutoGen GroupChat to intercept messages before delivery."""

    def wrap(self, guard: AgentGuard, group_chat: Any) -> Any:
        """Patch _process_received_message with AgentGuard inspection."""
        if not hasattr(group_chat, "_process_received_message"):
            msg = "Expected GroupChat with _process_received_message"
            raise TypeError(msg)
        original = group_chat._process_received_message
        group_chat._process_received_message = self._wrap_process(guard, original)  # noqa: SLF001
        return group_chat

    def _wrap_process(
        self,
        guard: AgentGuard,
        original_fn: Callable[..., Any],
    ) -> Callable[..., Any]:
        def wrapper(
            message: Any,
            sender: Any,
            recipient: Any,
            *args: object,
            **kwargs: object,
        ) -> Any:
            sender_id = getattr(sender, "name", str(sender))
            recipient_id = getattr(recipient, "name", str(recipient))
            if isinstance(message, str):
                text = message
            else:
                text = str(getattr(message, "content", message))
            payload = text.encode("utf-8")
            signature = None
            if guard.enable_trust_attestation:
                try:
                    signature = guard.sign_payload(sender_id, payload)
                except KeyError:
                    signature = None
            decision = guard.inspect_message(
                sender_id,
                recipient_id,
                text,
                payload,
                signature=signature,
            )
            if decision.action in (ACTION_QUARANTINE, ACTION_BLOCK):
                raise AgentGuardException(
                    action=decision.action,
                    sender_id=sender_id,
                    recipient_id=recipient_id,
                    risk_score=decision.risk_score,
                    trust_result=decision.trust_result,
                    capability_result=decision.capability_result,
                    failure_reason=decision.failure_reason,
                )
            return original_fn(message, sender, recipient, *args, **kwargs)

        return wrapper
