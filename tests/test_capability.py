"""Tests for capability manifests and enforcement."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentguard.capability.enforcer import CapabilityEnforcer
from agentguard.capability.manifest import CapabilityManifest, _schema_path


def test_schema_bundled_in_package() -> None:
    """Schema must resolve inside the agentguard package (pip-install safe)."""
    path = _schema_path()
    assert path.is_file()
    assert path.name == "capability_manifest.schema.json"
    assert "schemas" in path.parts


def test_from_yaml(project_root: Path) -> None:
    manifest = CapabilityManifest.from_yaml(str(project_root / "manifests" / "writer.yaml"))
    assert manifest.agent_id == "writer"
    assert "draft_report" in manifest.permitted_tools


def test_comms_agent_manifest_accepts_endpoints(project_root: Path) -> None:
    manifest = CapabilityManifest.from_yaml(str(project_root / "manifests" / "comms_agent.yaml"))
    assert manifest.external_contact is True
    assert any(ep.startswith("https://api.example.com") for ep in manifest.permitted_endpoints)


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


def test_attenuate_intersects_endpoints() -> None:
    parent = CapabilityManifest(
        agent_id="parent",
        permitted_tools=["email_send"],
        permitted_endpoints=["https://api.example.com/", "https://hooks.slack.com/"],
        external_contact=True,
        can_spawn_agents=True,
        max_delegation_depth=2,
    )
    child = CapabilityManifest(
        agent_id="child",
        permitted_tools=["email_send"],
        permitted_endpoints=["https://api.example.com/", "https://evil.example/"],
        external_contact=True,
    )
    effective = parent.attenuate(child)
    assert effective.permitted_endpoints == ["https://api.example.com/"]
    assert effective.external_contact is True


def test_enforcer_delegated_agent_attenuation(project_root: Path) -> None:
    parent = CapabilityManifest.from_yaml(str(project_root / "manifests" / "orchestrator.yaml"))
    enforcer = CapabilityEnforcer()
    enforcer.register_agent("orchestrator", parent)
    child = CapabilityManifest(
        agent_id="sub-orchestrator",
        permitted_tools=["delegate_task", "publish_external"],
        forbidden_tools=[],
        can_spawn_agents=True,
        max_delegation_depth=2,
    )
    effective = enforcer.register_delegated_agent("orchestrator", child)
    assert "delegate_task" in effective.permitted_tools
    assert "publish_external" not in effective.permitted_tools
    assert effective.max_delegation_depth <= 1
    assert not enforcer.check_tool_call("sub-orchestrator", "publish_external").allowed


def test_enforcer_blocks_spawn_when_disabled(researcher_manifest: CapabilityManifest) -> None:
    enforcer = CapabilityEnforcer()
    enforcer.register_agent("researcher", researcher_manifest)
    child = CapabilityManifest(agent_id="sub", permitted_tools=["web_search"])
    with pytest.raises(ValueError, match="cannot spawn"):
        enforcer.register_delegated_agent("researcher", child)


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


def test_enforcer_endpoint_and_data_source(project_root: Path) -> None:
    manifest = CapabilityManifest.from_yaml(str(project_root / "manifests" / "comms_agent.yaml"))
    enforcer = CapabilityEnforcer()
    enforcer.register_agent("comms-agent", manifest)

    ok = enforcer.check_tool_call(
        "comms-agent",
        "email_send",
        endpoint="https://api.example.com/email/send",
    )
    assert ok.allowed

    bad_ep = enforcer.check_tool_call(
        "comms-agent",
        "email_send",
        endpoint="https://evil.example/exfil",
    )
    assert not bad_ep.allowed

    assert enforcer.check_data_source("comms-agent", "contact_directory").allowed
    assert not enforcer.check_data_source("comms-agent", "payroll_db").allowed


def test_enforcer_output_tokens(writer_manifest: CapabilityManifest) -> None:
    enforcer = CapabilityEnforcer()
    enforcer.register_agent("writer", writer_manifest)
    assert enforcer.check_output_tokens("writer", 100).allowed
    assert not enforcer.check_output_tokens("writer", writer_manifest.max_output_tokens + 1).allowed


def test_enforcer_spawn_depth_exhausted(project_root: Path) -> None:
    parent = CapabilityManifest.from_yaml(str(project_root / "manifests" / "orchestrator.yaml"))
    enforcer = CapabilityEnforcer()
    enforcer.register_agent("orchestrator", parent)
    # Exhaust depth: current_depth must be < max_delegation_depth (2)
    assert enforcer.check_spawn("orchestrator", current_depth=0).allowed
    assert enforcer.check_spawn("orchestrator", current_depth=1).allowed
    assert not enforcer.check_spawn("orchestrator", current_depth=2).allowed
    assert enforcer.get_manifest("orchestrator") is parent


def test_empty_data_sources_deny_by_default() -> None:
    manifest = CapabilityManifest(agent_id="locked", permitted_tools=["t"], allowed_data_sources=[])
    enforcer = CapabilityEnforcer()
    enforcer.register_agent("locked", manifest)
    assert not enforcer.check_data_source("locked", "anything").allowed
