from __future__ import annotations

import structlog

from cryptoscope_shared.logging import bind_tenant, bind_trace, configure_logging


def test_configure_logging_returns_logger() -> None:
    logger = configure_logging("test-service", "info")
    assert logger is not None
    assert logger._context.get("service") == "test-service"


def test_configure_logging_with_debug_level() -> None:
    logger = configure_logging("test", "debug")
    assert logger is not None


def test_bind_tenant_sets_contextvar() -> None:
    bind_tenant("tenant-1")
    ctx = structlog.contextvars.get_contextvars()
    assert ctx.get("tenant_id") == "tenant-1"


def test_bind_trace_sets_contextvar() -> None:
    bind_trace("trace-abc")
    ctx = structlog.contextvars.get_contextvars()
    assert ctx.get("trace_id") == "trace-abc"
