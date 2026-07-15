"""AgentGuard — inter-agent security firewall for multi-agent AI systems."""

from agentguard.capability.manifest import CapabilityManifest
from agentguard.exceptions import AgentGuardException
from agentguard.firewall import AgentGuard

__all__ = ["AgentGuard", "AgentGuardException", "CapabilityManifest"]

__version__ = "1.0.0"
