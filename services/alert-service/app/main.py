from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from cryptoscope_shared.kafka import JsonConsumer, JsonProducer
from cryptoscope_shared.logging import configure_logging
from cryptoscope_shared.tracing import setup_tracing
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.routes import router
from app.infra.consumer import AlertEngine
from app.infra.db import build_engine, build_session_factory
from app.infra.notify import (
    EmailChannel,
    NotificationDispatcher,
    SlackWebhookChannel,
    WebhookChannel,
)
from app.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> Any:
    settings: Settings = app.state.settings
    logger = configure_logging(settings.service_name, settings.log_level)
    setup_tracing(settings.service_name, settings.otel_namespace, settings.otel_endpoint)

    engine = build_engine(settings.sqlalchemy_dsn)
    app.state.session_factory = build_session_factory(engine)

    consumer = JsonConsumer(settings.kafka_broker_list, settings.events_topic, "alert-service")
    await consumer.start()

    producer = JsonProducer(settings.kafka_broker_list)
    await producer.start()

    dispatcher = _build_dispatcher(settings)
    if dispatcher._channels:
        logger.info("notification channels enabled", count=len(dispatcher._channels))
    else:
        logger.info("no notification channels configured")

    alert_engine = AlertEngine(
        consumer, producer, settings.alerts_topic,
        app.state.session_factory, logger, dispatcher,
    )
    engine_task = asyncio.create_task(alert_engine.run())

    logger.info("alert service started", port=settings.http_port)
    try:
        yield
    finally:
        engine_task.cancel()
        await consumer.stop()
        await producer.stop()
        await engine.dispose()
        logger.info("alert service stopped")


def _build_dispatcher(settings: Settings) -> NotificationDispatcher:
    dispatcher = NotificationDispatcher()

    if settings.smtp_host and settings.smtp_from and settings.smtp_to:
        to_addrs = [a.strip() for a in settings.smtp_to.split(",") if a.strip()]
        dispatcher.add_channel(
            EmailChannel(
                smtp_host=settings.smtp_host,
                smtp_port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password,
                from_addr=settings.smtp_from,
                to_addrs=to_addrs,
            )
        )

    if settings.slack_webhook_url:
        dispatcher.add_channel(SlackWebhookChannel(settings.slack_webhook_url))

    if settings.webhook_url:
        headers = {}
        if settings.webhook_auth_header:
            headers["Authorization"] = settings.webhook_auth_header
        dispatcher.add_channel(WebhookChannel(settings.webhook_url, headers))

    return dispatcher


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="cryptoscope alert service", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(router)

    FastAPIInstrumentor.instrument_app(app)
    return app


app = create_app()
