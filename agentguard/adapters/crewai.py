"""CrewAI adapter for AgentGuard."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agentguard.exceptions import AgentGuardException
from agentguard.firewall import ACTION_BLOCK, ACTION_QUARANTINE, AgentGuard
from agentguard.mcp.output_inspector import MCPPoisoningException


class CrewAIAdapter:
    """Wraps CrewAI crews to intercept agent tasks and tool outputs."""

    def wrap(self, guard: AgentGuard, crew: Any) -> Any:
        """Patch crew agents and tools with AgentGuard interception."""
        for agent in getattr(crew, "agents", []) or []:
            agent_id = getattr(agent, "role", "crew_agent")
            if hasattr(agent, "execute_task"):
                original = agent.execute_task
                agent.execute_task = self._wrap_agent_execute(guard, agent_id, original)
        for tool in getattr(crew, "tools", []) or []:
            if hasattr(tool, "_run"):
                agent_id = getattr(tool, "agent_id", "crew_tool")
                tool._run = guard.wrap_mcp_tool(tool._run, agent_id)  # noqa: SLF001
        return crew

    def _wrap_agent_execute(
        self,
        guard: AgentGuard,
        agent_id: str,
        original_fn: Callable[..., Any],
    ) -> Callable[..., Any]:
        def wrapper(task: Any, *args: object, **kwargs: object) -> Any:
            message = task if isinstance(task, str) else str(getattr(task, "description", task))
            payload = message.encode("utf-8")
            signature = None
            if guard.enable_trust_attestation:
                try:
                    signature = guard.sign_payload(agent_id, payload)
                except KeyError:
                    signature = None
            decision = guard.inspect_message(
                agent_id, "crew_task", message, payload, signature=signature,
            )
            if decision.action in (ACTION_QUARANTINE, ACTION_BLOCK):
                raise AgentGuardException(
                    action=decision.action,
                    sender_id=agent_id,
                    recipient_id="crew_task",
                    risk_score=decision.risk_score,
                    trust_result=decision.trust_result,
                    capability_result=decision.capability_result,
                    failure_reason=decision.failure_reason,
                )
            result = original_fn(task, *args, **kwargs)
            output = result if isinstance(result, str) else str(result)
            inspection = guard._mcp_inspector.inspect_output("task_output", output, agent_id)  # noqa: SLF001
            if not inspection.safe:
                raise MCPPoisoningException(
                    tool_name="task_output",
                    agent_id=agent_id,
                    risk_score=inspection.risk_score,
                    flagged_patterns=inspection.flagged_patterns,
                )
            return result

        return wrapper
