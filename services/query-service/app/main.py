from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from cryptoscope_shared.logging import configure_logging
from cryptoscope_shared.tracing import setup_tracing
from fastapi import FastAPI
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.grpc_server import serve_grpc
from app.api.routes import router
from app.domain.service import QueryService
from app.infra.clickhouse_repo import CHConfig, ClickHousePool, ClickHouseReadRepository
from app.settings import Settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    logger = configure_logging(settings.service_name, settings.log_level)
    setup_tracing(settings.service_name, settings.otel_namespace, settings.otel_endpoint)

    pool = ClickHousePool(
        CHConfig(
            host=settings.clickhouse_host,
            port=settings.clickhouse_http_port,
            database=settings.clickhouse_db,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
        )
    )
    repo = ClickHouseReadRepository(pool)
    service = QueryService(repo)
    app.state.query_service = service

    grpc_server = await serve_grpc(service, settings.grpc_port)
    logger.info("query service started", http_port=settings.http_port, grpc_port=settings.grpc_port)
    try:
        yield
    finally:
        await grpc_server.stop(grace=5)
        pool.close()
        logger.info("query service stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    app = FastAPI(title="cryptoscope query service", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(router)

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    FastAPIInstrumentor.instrument_app(app)
    return app


app = create_app()
