"""Structured JSON logging built on structlog.

Every service logs the same shape so the log aggregation stack can index the
fields it cares about, in particular the tenant and trace identifiers.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(service: str, level: str = "info") -> structlog.BoundLogger:
    """Configure structlog for JSON output and return a bound logger."""

    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger().bind(service=service)


def bind_tenant(tenant_id: str) -> None:
    """Attach the tenant id to the current context so it appears on every log."""

    structlog.contextvars.bind_contextvars(tenant_id=tenant_id)


def bind_trace(trace_id: str) -> None:
    """Attach the trace id to the current context."""

    structlog.contextvars.bind_contextvars(trace_id=trace_id)
