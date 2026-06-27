"""YAML capability manifest loading and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import jsonschema
import yaml

_SCHEMA_PATH = Path(__file__).resolve().parents[2] / "schemas" / "capability_manifest.schema.json"


def _load_schema() -> dict[str, Any]:
    with _SCHEMA_PATH.open(encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


@dataclass
class CapabilityManifest:
    """Declarative runtime capability scope for an agent."""

    agent_id: str
    permitted_tools: list[str] = field(default_factory=list)
    forbidden_tools: list[str] = field(default_factory=list)
    allowed_data_sources: list[str] = field(default_factory=list)
    max_output_tokens: int = 4096
    external_contact: bool = False
    can_spawn_agents: bool = False
    max_delegation_depth: int = 0

    @classmethod
    def from_yaml(cls, path: str) -> CapabilityManifest:
        """Load and validate a manifest from a YAML file.

        Args:
            path: Path to the YAML manifest file.

        Returns:
            Validated CapabilityManifest instance.

        Raises:
            jsonschema.ValidationError: If validation fails.
            ValueError: If YAML content is invalid.
        """
        yaml_path = Path(path)
        with yaml_path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
        if not isinstance(data, dict):
            msg = f"Invalid manifest YAML in {yaml_path}"
            raise ValueError(msg)
        jsonschema.validate(instance=data, schema=_load_schema())
        return cls(
            agent_id=str(data["agent_id"]),
            permitted_tools=list(data.get("permitted_tools", [])),
            forbidden_tools=list(data.get("forbidden_tools", [])),
            allowed_data_sources=list(data.get("allowed_data_sources", [])),
            max_output_tokens=int(data.get("max_output_tokens", 4096)),
            external_contact=bool(data.get("external_contact", False)),
            can_spawn_agents=bool(data.get("can_spawn_agents", False)),
            max_delegation_depth=int(data.get("max_delegation_depth", 0)),
        )

    def is_tool_permitted(self, tool_name: str) -> bool:
        """Return True if the tool is explicitly permitted and not forbidden."""
        if tool_name in self.forbidden_tools:
            return False
        return tool_name in self.permitted_tools

    def attenuate(self, other: CapabilityManifest) -> CapabilityManifest:
        """Return monotonic attenuation: intersection of both manifests.

        Args:
            other: Sub-agent manifest to attenuate against this manifest.

        Returns:
            New manifest with reduced (never expanded) permissions.
        """
        permitted = sorted(set(self.permitted_tools) & set(other.permitted_tools))
        forbidden = sorted(set(self.forbidden_tools) | set(other.forbidden_tools))
        permitted = [tool for tool in permitted if tool not in forbidden]
        return CapabilityManifest(
            agent_id=other.agent_id,
            permitted_tools=permitted,
            forbidden_tools=forbidden,
            allowed_data_sources=sorted(
                set(self.allowed_data_sources) & set(other.allowed_data_sources),
            ),
            max_output_tokens=min(self.max_output_tokens, other.max_output_tokens),
            external_contact=self.external_contact and other.external_contact,
            can_spawn_agents=self.can_spawn_agents and other.can_spawn_agents,
            max_delegation_depth=min(self.max_delegation_depth, other.max_delegation_depth),
        )
