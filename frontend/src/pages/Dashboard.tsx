import { useCallback, useEffect, useState } from "react";
import { client } from "../api/client";
import type { AlertRule, AlertTrigger, Candle } from "../types";

function StatCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
      <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
      <p className={`text-2xl font-semibold mt-1 ${color || "text-gray-100"}`}>
        {value}
      </p>
    </div>
  );
}

export default function Dashboard() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [triggers, setTriggers] = useState<AlertTrigger[]>([]);
  const [btcCandle, setBtcCandle] = useState<Candle | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [s, r, t] = await Promise.all([
        client.listSymbols(),
        client.listAlertRules(),
        client.listTriggers(),
      ]);
      setSymbols(s.symbols);
      setRules(r);
      setTriggers(t);

      if (s.symbols.length > 0) {
        const sym = s.symbols[0];
        const cc = await client.getCandles(sym, "1h", undefined, undefined);
        if (cc.candles.length > 0) {
          setBtcCandle(cc.candles[cc.candles.length - 1]);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const activeRules = rules.filter((r) => r.status === "active").length;
  const unacked = triggers.filter((t) => !t.acknowledged).length;
  const lastTrigger = triggers.length > 0 ? triggers[0] : null;

  if (error) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400">
        {error}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold">Dashboard</h2>
        <p className="text-sm text-gray-500 mt-1">
          Platform overview at a glance
        </p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Tracked Symbols" value={String(symbols.length)} color="text-violet-400" />
        <StatCard label="Alert Rules" value={String(rules.length)} color="text-amber-400" />
        <StatCard label="Active Rules" value={String(activeRules)} color="text-green-400" />
        <StatCard
          label="Unacknowledged Triggers"
          value={String(unacked)}
          color={unacked > 0 ? "text-red-400" : "text-gray-400"}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {btcCandle && (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">
              Latest Candle — {symbols[0]}
            </h3>
            <div className="grid grid-cols-3 gap-3 text-sm">
              <div>
                <span className="text-gray-500">Open</span>
                <p className="font-mono">{btcCandle.open.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-gray-500">High</span>
                <p className="font-mono text-green-400">{btcCandle.high.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-gray-500">Low</span>
                <p className="font-mono text-red-400">{btcCandle.low.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-gray-500">Close</span>
                <p className="font-mono">{btcCandle.close.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-gray-500">Volume</span>
                <p className="font-mono">{btcCandle.volume.toFixed(2)}</p>
              </div>
              <div>
                <span className="text-gray-500">Change</span>
                <p
                  className={`font-mono ${
                    btcCandle.close >= btcCandle.open
                      ? "text-green-400"
                      : "text-red-400"
                  }`}
                >
                  {((btcCandle.close - btcCandle.open) / btcCandle.open * 100).toFixed(2)}%
                </p>
              </div>
            </div>
          </div>
        )}

        {lastTrigger && (
          <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">
              Most Recent Trigger
            </h3>
            <div className="text-sm space-y-1">
              <p>
                <span className="text-gray-500">Symbol:</span>{" "}
                <span className="font-mono">{lastTrigger.symbol}</span>
              </p>
              <p>
                <span className="text-gray-500">Rule:</span>{" "}
                <span className="font-mono">{lastTrigger.rule_id.slice(0, 8)}</span>
              </p>
              <p>
                <span className="text-gray-500">Trigger:</span>{" "}
                <span className="font-mono">
                  {lastTrigger.comparator} {lastTrigger.threshold}
                </span>
              </p>
              <p>
                <span className="text-gray-500">Value:</span>{" "}
                <span className="font-mono">{lastTrigger.current_value.toFixed(2)}</span>
              </p>
              <p>
                <span className="text-gray-500">At:</span>{" "}
                <span className="font-mono text-xs">
                  {new Date(lastTrigger.triggered_at).toLocaleString()}
                </span>
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">
          Tracked Symbols
        </h3>
        {symbols.length === 0 ? (
          <p className="text-sm text-gray-500">No symbols tracked yet.</p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {symbols.map((s) => (
              <span
                key={s}
                className="px-3 py-1 rounded-full bg-gray-800 text-gray-300 text-xs font-mono"
              >
                {s}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
