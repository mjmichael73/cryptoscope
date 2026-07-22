import { useCallback, useEffect, useState } from "react";
import { client } from "../api/client";

interface ServiceStatus {
  name: string;
  status: string;
  endpoint: string;
}

const SERVICES: ServiceStatus[] = [
  { name: "API Gateway", status: "checking...", endpoint: "/healthz" },
  { name: "Alert Service", status: "checking...", endpoint: "/healthz" },
  { name: "Query Service", status: "checking...", endpoint: "/candles?symbol=BTCUSDT&interval=1h" },
  { name: "Command Service", status: "checking...", endpoint: "POST /watchlists" },
];

export default function Health() {
  const [services, setServices] = useState(SERVICES);

  const check = useCallback(async () => {
    const updates = [...services];

    try {
      const h = await client.health();
      updates[0] = { ...updates[0], status: h.status };
    } catch {
      updates[0] = { ...updates[0], status: "unreachable" };
    }

    try {
      const symbols = await client.listSymbols();
      updates[2] = {
        ...updates[2],
        status: `ok (${symbols.symbols.length} symbols)`,
      };
    } catch {
      updates[2] = { ...updates[2], status: "unreachable" };
    }

    try {
      const h = await client.alertHealth();
      updates[1] = { ...updates[1], status: h.status };
    } catch {
      updates[1] = { ...updates[1], status: "unreachable" };
    }

    try {
      const h = await client.commandHealth();
      updates[3] = { ...updates[3], status: h.status };
    } catch {
      updates[3] = { ...updates[3], status: "unreachable" };
    }

    setServices(updates);
  }, [services]);

  useEffect(() => {
    check();
  }, []);

  const allOk = services.every(
    (s) => s.status !== "unreachable" && s.status !== "checking...",
  );

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h2 className="text-xl font-bold">System Health</h2>
        <p className="text-sm text-gray-500 mt-1">
          Service status and connectivity
        </p>
      </div>

      <div
        className={`rounded-lg border p-4 ${
          allOk
            ? "border-green-800 bg-green-900/20"
            : "border-red-800 bg-red-900/20"
        }`}
      >
        <p className="text-sm font-medium">
          Overall Status:{" "}
          <span className={allOk ? "text-green-400" : "text-red-400"}>
            {allOk ? "All Systems Operational" : "Issues Detected"}
          </span>
        </p>
      </div>

      <div className="space-y-3">
        {services.map((svc) => (
          <div
            key={svc.name}
            className="rounded-lg border border-gray-800 bg-gray-900 p-4 flex items-center justify-between"
          >
            <div>
              <h3 className="text-sm font-medium text-gray-200">{svc.name}</h3>
              <p className="text-xs text-gray-500 mt-0.5">{svc.endpoint}</p>
            </div>
            <span
              className={`text-xs px-2.5 py-1 rounded-full font-medium ${
                svc.status === "ok" ||
                svc.status.startsWith("ok")
                  ? "bg-green-900/30 text-green-400"
                  : svc.status === "checking..."
                    ? "bg-gray-800 text-gray-500"
                    : "bg-red-900/30 text-red-400"
              }`}
            >
              {svc.status}
            </span>
          </div>
        ))}
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-2">
          Architecture
        </h3>
        <pre className="text-xs text-gray-500 leading-relaxed font-mono">
{`Exchange APIs (Binance, Coinbase)
        │
        ▼
  ingest-service (Go) ──► Kafka (market.ticks.raw)
        │
        ▼
  stream-processor (Go) ──► ClickHouse (candles)
                          ──► Mongo   (latest state)
        │
        ├── query-service (Python) ◄── gRPC ── api-gateway (Go) ◄── HTTP ── Frontend
        │
        └── command-service (Python) ◄── HTTP ── api-gateway (Go) ◄── HTTP ── Frontend
                 │
                 └──► Kafka (domain.events) ──► alert-service (Python)
                                                      │
                                                      └──► PostgreSQL (alert_triggers)`}
        </pre>
      </div>
    </div>
  );
}
