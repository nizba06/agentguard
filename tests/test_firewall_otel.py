"""Tests for firewall OpenTelemetry integration."""

from __future__ import annotations

from unittest.mock import MagicMock

from agentguard import AgentGuard
from agentguard.capability.manifest import CapabilityManifest


def test_firewall_exports_audit_entry_to_otel(
    researcher_manifest: CapabilityManifest,
    tmp_path,
) -> None:
    mock_otel = MagicMock()
    guard = AgentGuard(
        audit_log_path=str(tmp_path / "audit.jsonl"),
        enable_otel_export=True,
    )
    guard._otel = mock_otel
    guard.register_agent("researcher", researcher_manifest)

    payload = b"Summarise public pricing data from filings."
    sig = guard.sign_payload("researcher", payload)
    guard.inspect_message("researcher", "writer", payload.decode(), payload, signature=sig)

    mock_otel.export_entry.assert_called_once()
    exported = mock_otel.export_entry.call_args[0][0]
    assert exported.sender_id == "researcher"
    assert exported.recipient_id == "writer"
