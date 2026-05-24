"""OpenTelemetry setup for the Python services.

A single call installs a tracer provider that exports spans to the OTel
Collector over gRPC. FastAPI apps are instrumented separately by the service
so this stays framework agnostic.
"""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def setup_tracing(service: str, namespace: str, endpoint: str) -> TracerProvider:
    """Install a global tracer provider and return it for later shutdown."""

    resource = Resource.create(
        {
            "service.name": service,
            "service.namespace": namespace,
        }
    )
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return provider
