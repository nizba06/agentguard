"""Tests for optional OpenTelemetry audit export."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agentguard.audit.logger import AppendOnlyLogger
from agentguard.audit.otel import AuditOtelExporter, create_otel_exporter_if_configured


def test_create_otel_exporter_without_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert create_otel_exporter_if_configured() is None


def test_create_otel_exporter_with_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    mock_tracer = MagicMock()
    mock_span = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

    with patch.dict(
        "sys.modules",
        {
            "opentelemetry": MagicMock(
                trace=MagicMock(
                    get_tracer=MagicMock(return_value=mock_tracer),
                    set_tracer_provider=MagicMock(),
                )
            ),
            "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": MagicMock(
                OTLPSpanExporter=MagicMock(),
            ),
            "opentelemetry.sdk.resources": MagicMock(Resource=MagicMock()),
            "opentelemetry.sdk.trace": MagicMock(TracerProvider=MagicMock()),
            "opentelemetry.sdk.trace.export": MagicMock(BatchSpanProcessor=MagicMock()),
        },
    ):
        exporter = create_otel_exporter_if_configured()
    assert exporter is not None


def test_export_entry_sets_span_attributes() -> None:
    logger = AppendOnlyLogger()
    entry = logger.write_entry(
        sender_id="a",
        recipient_id="b",
        risk_score=0.42,
        trust_result="PASS",
        capability_result="SKIP",
        action="FORWARD",
        failure_reason="rule_filter",
        message_preview="preview",
        payload_bytes=b"payload",
    )

    mock_span = MagicMock()
    mock_tracer = MagicMock()
    mock_tracer.start_as_current_span.return_value.__enter__ = MagicMock(return_value=mock_span)
    mock_tracer.start_as_current_span.return_value.__exit__ = MagicMock(return_value=False)

    exporter = AuditOtelExporter.__new__(AuditOtelExporter)
    exporter._tracer = mock_tracer
    exporter.export_entry(entry)

    mock_tracer.start_as_current_span.assert_called_once_with("agentguard.inspect")
    mock_span.set_attribute.assert_any_call("agentguard.sender_id", "a")
    mock_span.set_attribute.assert_any_call("agentguard.risk_score", 0.42)
    mock_span.set_attribute.assert_any_call("agentguard.failure_reason", "rule_filter")


def test_audit_otel_exporter_missing_dependency() -> None:
    with patch.dict("sys.modules", {"opentelemetry": None}):
        with pytest.raises(RuntimeError, match="agentguard\\[otel\\]"):
            AuditOtelExporter()
