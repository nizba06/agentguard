"""Tests for capability manifests and enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentguard.capability.enforcer import CapabilityEnforcer
from agentguard.capability.manifest import CapabilityManifest


def test_from_yaml(project_root: Path) -> None:
    manifest = CapabilityManifest.from_yaml(str(project_root / "manifests" / "writer.yaml"))
    assert manifest.agent_id == "writer"
    assert "draft_report" in manifest.permitted_tools


def test_invalid_manifest_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("agent_id: only-id\n", encoding="utf-8")
    with pytest.raises(Exception):
        CapabilityManifest.from_yaml(str(bad))


def test_is_tool_permitted(writer_manifest: CapabilityManifest) -> None:
    assert writer_manifest.is_tool_permitted("draft_report")
    assert not writer_manifest.is_tool_permitted("publish_external")
    assert not writer_manifest.is_tool_permitted("unknown_tool")


def test_attenuate_monotonic(researcher_manifest: CapabilityManifest) -> None:
    child = CapabilityManifest(
        agent_id="sub",
        permitted_tools=["web_search", "publish_external"],
        forbidden_tools=[],
    )
    effective = researcher_manifest.attenuate(child)
    assert "web_search" in effective.permitted_tools
    assert "publish_external" not in effective.permitted_tools


def test_enforcer_blocks_forbidden(writer_manifest: CapabilityManifest) -> None:
    enforcer = CapabilityEnforcer()
    enforcer.register_agent("writer", writer_manifest)
    allowed = enforcer.check_tool_call("writer", "draft_report")
    blocked = enforcer.check_tool_call("writer", "publish_external")
    assert allowed.allowed
    assert not blocked.allowed
    assert blocked.reason


def test_enforcer_unregistered_agent() -> None:
    enforcer = CapabilityEnforcer()
    result = enforcer.check_tool_call("unknown", "any_tool")
    assert not result.allowed
