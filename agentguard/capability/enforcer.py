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
    """Enforces capability manifests at tool-call and related control points."""

    def __init__(self) -> None:
        self._manifests: dict[str, CapabilityManifest] = {}

    def register_agent(self, agent_id: str, manifest: CapabilityManifest) -> None:
        """Register an agent manifest for runtime enforcement.

        Args:
            agent_id: Agent identifier.
            manifest: Validated capability manifest.
        """
        self._manifests[agent_id] = manifest

    def get_manifest(self, agent_id: str) -> CapabilityManifest | None:
        """Return the registered manifest for an agent, if any."""
        return self._manifests.get(agent_id)

    def register_delegated_agent(
        self,
        parent_agent_id: str,
        child_manifest: CapabilityManifest,
    ) -> CapabilityManifest:
        """Register a sub-agent with monotonic attenuation against the parent manifest.

        Args:
            parent_agent_id: Delegating agent identifier.
            child_manifest: Sub-agent manifest to attenuate.

        Returns:
            Effective manifest stored for the child agent.

        Raises:
            KeyError: If the parent agent is not registered.
            ValueError: If the parent cannot spawn agents or depth is exhausted.
        """
        parent = self._manifests[parent_agent_id]
        spawn = self.check_spawn(parent_agent_id, current_depth=0)
        if not spawn.allowed:
            raise ValueError(spawn.reason)
        effective = parent.attenuate(child_manifest)
        # Child depth budget is one less than parent remaining depth.
        if parent.max_delegation_depth > 0:
            effective.max_delegation_depth = min(
                effective.max_delegation_depth,
                parent.max_delegation_depth - 1,
            )
        self._manifests[child_manifest.agent_id] = effective
        return effective

    def check_tool_call(
        self,
        agent_id: str,
        tool_name: str,
        *,
        endpoint: str | None = None,
    ) -> EnforcementResult:
        """Validate a tool call against the agent's manifest.

        Args:
            agent_id: Calling agent identifier.
            tool_name: Requested tool name.
            endpoint: Optional external URL the tool would contact.

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
        if endpoint is not None:
            return self.check_endpoint(agent_id, endpoint)
        return EnforcementResult(allowed=True, reason="ok")

    def check_endpoint(self, agent_id: str, endpoint: str) -> EnforcementResult:
        """Validate an external endpoint against the agent's manifest."""
        manifest = self._manifests.get(agent_id)
        if manifest is None:
            return EnforcementResult(allowed=False, reason=f"unregistered agent: {agent_id}")
        if not manifest.external_contact:
            return EnforcementResult(
                allowed=False,
                reason="external_contact is disabled for this agent",
            )
        if not manifest.permitted_endpoints:
            return EnforcementResult(
                allowed=False,
                reason="no permitted_endpoints configured",
            )
        if not manifest.is_endpoint_permitted(endpoint):
            return EnforcementResult(
                allowed=False,
                reason=f"endpoint '{endpoint}' not in permitted_endpoints",
            )
        return EnforcementResult(allowed=True, reason="ok")

    def check_data_source(self, agent_id: str, data_source: str) -> EnforcementResult:
        """Validate a data-source access against the agent's manifest."""
        manifest = self._manifests.get(agent_id)
        if manifest is None:
            return EnforcementResult(allowed=False, reason=f"unregistered agent: {agent_id}")
        if not manifest.is_data_source_allowed(data_source):
            return EnforcementResult(
                allowed=False,
                reason=f"data source '{data_source}' not in allowed_data_sources",
            )
        return EnforcementResult(allowed=True, reason="ok")

    def check_output_tokens(self, agent_id: str, token_count: int) -> EnforcementResult:
        """Validate an output token count against the agent's max_output_tokens."""
        manifest = self._manifests.get(agent_id)
        if manifest is None:
            return EnforcementResult(allowed=False, reason=f"unregistered agent: {agent_id}")
        if token_count < 0:
            return EnforcementResult(allowed=False, reason="token_count must be non-negative")
        if token_count > manifest.max_output_tokens:
            return EnforcementResult(
                allowed=False,
                reason=(
                    f"output tokens {token_count} exceed max_output_tokens "
                    f"{manifest.max_output_tokens}"
                ),
            )
        return EnforcementResult(allowed=True, reason="ok")

    def check_spawn(self, agent_id: str, *, current_depth: int = 0) -> EnforcementResult:
        """Validate whether an agent may spawn a sub-agent at the given depth."""
        manifest = self._manifests.get(agent_id)
        if manifest is None:
            return EnforcementResult(allowed=False, reason=f"unregistered agent: {agent_id}")
        if not manifest.can_spawn_agents:
            return EnforcementResult(
                allowed=False,
                reason=f"agent '{agent_id}' cannot spawn agents",
            )
        if current_depth >= manifest.max_delegation_depth:
            return EnforcementResult(
                allowed=False,
                reason=(
                    f"delegation depth {current_depth} exceeds "
                    f"max_delegation_depth {manifest.max_delegation_depth}"
                ),
            )
        return EnforcementResult(allowed=True, reason="ok")
