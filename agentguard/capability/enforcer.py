"""Runtime capability manifest enforcement."""

from __future__ import annotations

from dataclasses import dataclass

from agentguard.capability.manifest import CapabilityManifest


@dataclass(frozen=True)
class EnforcementResult:
    """Outcome of a capability enforcement check."""

    allowed: bool
    reason: str


class CapabilityEnforcer:
    """Enforces capability manifests at tool-call time."""

    def __init__(self) -> None:
        self._manifests: dict[str, CapabilityManifest] = {}

    def register_agent(self, agent_id: str, manifest: CapabilityManifest) -> None:
        """Register an agent manifest for runtime enforcement.

        Args:
            agent_id: Agent identifier.
            manifest: Validated capability manifest.
        """
        self._manifests[agent_id] = manifest

    def check_tool_call(self, agent_id: str, tool_name: str) -> EnforcementResult:
        """Validate a tool call against the agent's manifest.

        Args:
            agent_id: Calling agent identifier.
            tool_name: Requested tool name.

        Returns:
            EnforcementResult indicating allow or deny with reason.
        """
        manifest = self._manifests.get(agent_id)
        if manifest is None:
            return EnforcementResult(allowed=False, reason=f"unregistered agent: {agent_id}")
        if tool_name in manifest.forbidden_tools:
            return EnforcementResult(allowed=False, reason=f"tool '{tool_name}' is forbidden")
        if tool_name not in manifest.permitted_tools:
            return EnforcementResult(
                allowed=False,
                reason=f"tool '{tool_name}' not in permitted_tools",
            )
        return EnforcementResult(allowed=True, reason="ok")
