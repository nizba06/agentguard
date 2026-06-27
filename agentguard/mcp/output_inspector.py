"""MCP tool output inspection before agent ingestion."""

from __future__ import annotations

import functools
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from agentguard.exceptions import AgentGuardException
from agentguard.inspector.ml_scorer import MLRiskScorer
from agentguard.inspector.rule_filter import InjectionRuleFilter

F = TypeVar("F", bound=Callable[..., Any])


class MCPPoisoningException(AgentGuardException):
    """Raised when MCP tool output contains an injection payload."""

    def __init__(
        self,
        *,
        tool_name: str,
        agent_id: str,
        risk_score: float,
        flagged_patterns: list[str],
        action: str = "QUARANTINE",
        sender_id: str = "",
        recipient_id: str = "",
        trust_result: str = "SKIP",
        capability_result: str = "SKIP",
        failure_reason: str | None = None,
    ) -> None:
        super().__init__(
            action=action,
            sender_id=sender_id or agent_id,
            recipient_id=recipient_id or "mcp_tool",
            risk_score=risk_score,
            trust_result=trust_result,
            capability_result=capability_result,
            failure_reason=failure_reason or f"MCP output poisoned: {tool_name}",
        )
        self.tool_name = tool_name
        self.agent_id = agent_id
        self.flagged_patterns = flagged_patterns


@dataclass(frozen=True)
class MCPInspectionResult:
    """Result of inspecting an MCP tool return value."""

    safe: bool
    risk_score: float
    flagged_patterns: list[str]
    tool_name: str
    calling_agent_id: str


class MCPOutputInspector:
    """Inspects MCP server tool outputs for injection payloads."""

    def __init__(
        self,
        rule_filter: InjectionRuleFilter,
        ml_scorer: MLRiskScorer,
        threshold: float = 0.75,
    ) -> None:
        self._rule_filter = rule_filter
        self._ml_scorer = ml_scorer
        self._threshold = threshold

    def inspect_output(
        self,
        tool_name: str,
        output: str,
        calling_agent_id: str,
    ) -> MCPInspectionResult:
        """Score MCP tool output for injection risk."""
        rule = self._rule_filter.scan(output)
        ml_score = self._ml_scorer.score(output)
        risk = max(ml_score, 0.9 if rule.flagged else 0.0)
        flagged = rule.flagged or ml_score >= self._threshold
        patterns = list(rule.matched_rules) if rule.flagged else []
        return MCPInspectionResult(
            safe=not flagged,
            risk_score=risk,
            flagged_patterns=patterns,
            tool_name=tool_name,
            calling_agent_id=calling_agent_id,
        )

    def wrap_tool(self, tool_fn: F, guard: Any, agent_id: str) -> F:
        """Wrap a tool callable with MCP output inspection."""

        @functools.wraps(tool_fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = tool_fn(*args, **kwargs)
            text = result if isinstance(result, str) else str(result)
            tool_name = getattr(tool_fn, "__name__", "mcp_tool")
            inspection = self.inspect_output(tool_name, text, agent_id)
            if not inspection.safe:
                raise MCPPoisoningException(
                    tool_name=tool_name,
                    agent_id=agent_id,
                    risk_score=inspection.risk_score,
                    flagged_patterns=inspection.flagged_patterns,
                    failure_reason=(
                        f"mcp_output: {inspection.flagged_patterns[0]}"
                        if inspection.flagged_patterns
                        else f"mcp_output: risk={inspection.risk_score:.3f}"
                    ),
                )
            return result

        return wrapper  # type: ignore[return-value]
