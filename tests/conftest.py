"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from agentguard import AgentGuard
from agentguard.capability.manifest import CapabilityManifest


@pytest.fixture(autouse=True)
def _disable_auto_ml_model(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep bundled ONNX off by default so benign fixtures are not quarantined."""
    if request.node.get_closest_marker("ml_model"):
        return
    missing = Path("__agentguard_test_no_model__") / "risk_scorer.onnx"
    monkeypatch.setattr("agentguard.firewall.default_model_path", lambda: missing)


@pytest.fixture
def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def researcher_manifest(project_root: Path) -> CapabilityManifest:
    return CapabilityManifest.from_yaml(str(project_root / "manifests" / "researcher.yaml"))


@pytest.fixture
def writer_manifest(project_root: Path) -> CapabilityManifest:
    return CapabilityManifest.from_yaml(str(project_root / "manifests" / "writer.yaml"))


@pytest.fixture
def guard(researcher_manifest: CapabilityManifest, tmp_path: Path) -> AgentGuard:
    g = AgentGuard(
        audit_log_path=str(tmp_path / "audit.jsonl"),
        enable_trust_attestation=True,
    )
    g.register_agent("researcher", researcher_manifest)
    return g
