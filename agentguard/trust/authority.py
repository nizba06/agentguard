"""In-process Trust Authority for ephemeral agent identities."""

from __future__ import annotations

from dataclasses import dataclass

from agentguard.trust.signing import generate_keypair, sign_message


@dataclass
class _AgentKeys:
    public_key: bytes
    private_key: bytes


class TrustAuthority:
    """Generates and manages ephemeral Ed25519 keypairs in memory only."""

    def __init__(self) -> None:
        self._keys: dict[str, _AgentKeys] = {}

    def register_agent(self, agent_id: str) -> None:
        """Generate and store an ephemeral keypair for an agent.

        Args:
            agent_id: Unique agent identifier.

        Raises:
            ValueError: If the agent is already registered.
        """
        if agent_id in self._keys:
            msg = f"Agent already registered: {agent_id}"
            raise ValueError(msg)
        public_key, private_key = generate_keypair()
        self._keys[agent_id] = _AgentKeys(public_key=public_key, private_key=private_key)

    def get_public_key(self, agent_id: str) -> bytes:
        """Return the public key for a registered agent.

        Args:
            agent_id: Registered agent identifier.

        Returns:
            32-byte Ed25519 public key.

        Raises:
            KeyError: If the agent is not registered.
        """
        if agent_id not in self._keys:
            msg = f"Unknown agent: {agent_id}"
            raise KeyError(msg)
        return self._keys[agent_id].public_key

    def sign_for_agent(self, agent_id: str, message: bytes) -> bytes:
        """Sign a message with the agent's private key.

        Args:
            agent_id: Registered agent identifier.
            message: Raw message bytes.

        Returns:
            64-byte Ed25519 signature.

        Raises:
            KeyError: If the agent is not registered.
        """
        if agent_id not in self._keys:
            msg = f"Unknown agent: {agent_id}"
            raise KeyError(msg)
        return sign_message(message, self._keys[agent_id].private_key)

    def rotate_all_keys(self) -> None:
        """Regenerate keypairs for every registered agent (pipeline start)."""
        agent_ids = list(self._keys.keys())
        self._keys.clear()
        for agent_id in agent_ids:
            self.register_agent(agent_id)

    def registered_agents(self) -> list[str]:
        """Return registered agent identifiers."""
        return list(self._keys.keys())
