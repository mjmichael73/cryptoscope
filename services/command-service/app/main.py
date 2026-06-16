"""Command service entrypoint.

Builds the FastAPI app, wires the database, Kafka producer, logging, and
tracing, and exposes the write-side routes plus a health check.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from cryptoscope_shared.kafka import JsonProducer
from cryptoscope_shared.logging import configure_logging
from cryptoscope_shared.tracing import setup_tracing
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.routes import router
from app.infra.db import build_engine, build_session_factory
from app.infra.publisher import KafkaEventPublisher
from app.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    logger = configure_logging(settings.service_name, settings.log_level)
    setup_tracing(settings.service_name, settings.otel_namespace, settings.otel_endpoint)

    engine = build_engine(settings.sqlalchemy_dsn)
    app.state.session_factory = build_session_factory(engine)

    producer = JsonProducer(settings.kafka_broker_list)
    await producer.start()
    app.state.publisher = KafkaEventPublisher(producer, settings.events_topic)

    logger.info("command service started", port=settings.http_port)
    try:
        yield
    finally:
        await producer.stop()
        await engine.dispose()
        logger.info("command service stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="cryptoscope command service", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    FastAPIInstrumentor.instrument_app(app)
    return app


app = create_app()
