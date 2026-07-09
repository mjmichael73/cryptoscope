"""gRPC surface for the query service.

The servicer is a thin adapter over the same QueryService the REST routes use.
It runs the async use cases on the service event loop from the grpc.aio server
so both surfaces share one code path.
"""

from __future__ import annotations

import grpc
from cryptoscope_proto.cryptoscope.v1 import common_pb2, query_pb2, query_pb2_grpc

from app.domain.errors import ValidationError
from app.domain.service import QueryService

_INTERVAL_NAMES = {
    common_pb2.INTERVAL_1M: "1m",
    common_pb2.INTERVAL_5M: "5m",
    common_pb2.INTERVAL_1H: "1h",
    common_pb2.INTERVAL_1D: "1d",
}


def _interval_name(value: int) -> str:
    return _INTERVAL_NAMES.get(value, "1m")


class QueryServicer(query_pb2_grpc.QueryServiceServicer):
    def __init__(self, service: QueryService) -> None:
        self._service = service

    async def GetCandles(self, request, context):
        try:
            candles = await self._service.get_candles(
                request.tenant_id,
                request.symbol,
                _interval_name(request.interval),
                request.from_ms,
                request.to_ms,
            )
        except ValidationError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return query_pb2.GetCandlesResponse(
            candles=[
                query_pb2.Candle(
                    open_time=c.open_time_ms,
                    open=c.open,
                    high=c.high,
                    low=c.low,
                    close=c.close,
                    volume=c.volume,
                )
                for c in candles
            ]
        )

    async def GetIndicator(self, request, context):
        try:
            points = await self._service.get_indicator(
                request.tenant_id,
                request.symbol,
                _interval_name(request.interval),
                request.type,
                request.period,
                0,
                2**63 - 1,
            )
        except ValidationError as exc:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return query_pb2.GetIndicatorResponse(
            points=[
                query_pb2.IndicatorPoint(time=p.time_ms, value=p.value) for p in points
            ]
        )

    async def ListSymbols(self, request, context):
        symbols = await self._service.list_symbols(request.tenant_id)
        return query_pb2.ListSymbolsResponse(symbols=symbols)


async def serve_grpc(service: QueryService, port: int) -> grpc.aio.Server:
    server = grpc.aio.server()
    query_pb2_grpc.add_QueryServiceServicer_to_server(QueryServicer(service), server)
    server.add_insecure_port(f"[::]:{port}")
    await server.start()
    return server
