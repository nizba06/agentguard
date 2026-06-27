"""AgentGuard public exceptions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentGuardException(Exception):  # noqa: N818
    """Raised when AgentGuard blocks or quarantines an inter-agent message."""

    action: str
    sender_id: str
    recipient_id: str
    risk_score: float
    trust_result: str
    capability_result: str
    failure_reason: str | None

    def __str__(self) -> str:
        return (
            f"AgentGuard {self.action}: {self.failure_reason or 'security check failed'} "
            f"(sender={self.sender_id}, recipient={self.recipient_id}, "
            f"risk={self.risk_score:.3f})"
        )
