"""Optional OpenTelemetry export for audit log entries."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agentguard.audit.logger import AuditLogEntry


class AuditOtelExporter:
    """Exports audit entries as OpenTelemetry spans (optional dependency)."""

    def __init__(self, service_name: str = "agentguard") -> None:
        self._tracer: Any | None = None
        try:
            from opentelemetry import trace  # noqa: PLC0415
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # noqa: PLC0415
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.resources import Resource  # noqa: PLC0415
            from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
            from opentelemetry.sdk.trace.export import BatchSpanProcessor  # noqa: PLC0415
        except ImportError as exc:
            msg = 'OpenTelemetry export requires: pip install "inter-agent-guard[otel]"'
            raise RuntimeError(msg) from exc

        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=endpoint) if endpoint else OTLPSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer("agentguard.audit")

    def export_entry(self, entry: AuditLogEntry) -> None:
        """Record one audit log entry as a span."""
        if self._tracer is None:
            return
        with self._tracer.start_as_current_span("agentguard.inspect") as span:
            span.set_attribute("agentguard.entry_id", entry.entry_id)
            span.set_attribute("agentguard.sender_id", entry.sender_id)
            span.set_attribute("agentguard.recipient_id", entry.recipient_id)
            span.set_attribute("agentguard.action", entry.action)
            span.set_attribute("agentguard.trust_result", entry.trust_result)
            span.set_attribute("agentguard.capability_result", entry.capability_result)
            if entry.risk_score is not None:
                span.set_attribute("agentguard.risk_score", entry.risk_score)
            if entry.failure_reason:
                span.set_attribute("agentguard.failure_reason", entry.failure_reason)


def create_otel_exporter_if_configured() -> AuditOtelExporter | None:
    """Create exporter when OTEL_EXPORTER_OTLP_ENDPOINT is set."""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return None
    return AuditOtelExporter()
