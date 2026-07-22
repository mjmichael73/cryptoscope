from __future__ import annotations

from unittest.mock import patch

from cryptoscope_shared.tracing import setup_tracing


@patch("cryptoscope_shared.tracing.OTLPSpanExporter")
@patch("cryptoscope_shared.tracing.TracerProvider")
def test_setup_tracing_creates_provider(
    mock_provider: patch, mock_exporter: patch
) -> None:
    provider = setup_tracing(
        service="test-service",
        namespace="cryptoscope",
        endpoint="http://localhost:4317",
    )
    assert provider is not None
