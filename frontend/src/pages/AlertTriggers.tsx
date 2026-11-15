import { useCallback, useEffect, useState } from "react";
import { client } from "../api/client";
import type { AlertTrigger } from "../types";

type Filter = "all" | "unacked";

function comparatorLabel(comparator: string): string {
  switch (comparator) {
    case "above":
      return "Above";
    case "below":
      return "Below";
    case "crosses_above":
      return "Crossed above";
    case "crosses_below":
      return "Crossed below";
    case "pct_change_above":
      return "Rallied";
    case "pct_change_below":
      return "Dropped";
    case "rsi_above":
      return "RSI above";
    case "rsi_below":
      return "RSI below";
    default:
      return comparator;
  }
}

function valueSuffix(comparator: string): string {
  return comparator.startsWith("pct_change") ? "%" : "";
}

function formatWindow(seconds: number | null): string {
  if (seconds == null) return "";
  if (seconds >= 3600 && seconds % 3600 === 0) return `${seconds / 3600}h`;
  if (seconds >= 60 && seconds % 60 === 0) return `${seconds / 60}m`;
  return `${seconds}s`;
}

export default function AlertTriggers() {
  const [triggers, setTriggers] = useState<AlertTrigger[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<Filter>("all");
  const [ackingId, setAckingId] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);
  const [clearMessage, setClearMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTriggers(await client.listTriggers(undefined, 100));
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const clearHistory = async (acknowledgedOnly: boolean) => {
    if (!acknowledgedOnly && !window.confirm('Clear all trigger history?')) return;
    setClearing(true);
    setClearMessage(null);
    try {
      const result = await client.clearTriggers(acknowledgedOnly);
      setClearMessage(`${result.deleted} trigger${result.deleted === 1 ? '' : 's'} cleared`);
      await load();
    } catch {
      setClearMessage('Trigger history could not be cleared.');
    } finally {
      setClearing(false);
    }
  };

  const ack = async (triggerId: string) => {
    setAckingId(triggerId);
    try {
      const updated = await client.ackTrigger(triggerId);
      setTriggers((prev) => prev.map((t) => (t.id === updated.id ? updated : t)));
    } catch {
      // silent — the row stays pending and the user can retry
    } finally {
      setAckingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Loading...
      </div>
    );
  }

  const unackedCount = triggers.filter((t) => !t.acknowledged).length;
  const visible =
    filter === "unacked" ? triggers.filter((t) => !t.acknowledged) : triggers;
  const acknowledgedCount = triggers.filter((trigger) => trigger.acknowledged).length;

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-xl font-bold">Alert Triggers</h2>
        <p className="text-sm text-gray-500 mt-1">
          History of triggered alert events — acknowledge events once handled
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {(
            [
              ["all", `All (${triggers.length})`],
              ["unacked", `Unacknowledged (${unackedCount})`],
            ] as [Filter, string][]
          ).map(([value, label]) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              aria-pressed={filter === value}
              className={`min-h-11 rounded-lg px-3 text-sm font-medium transition-colors ${
                filter === value
                  ? "bg-violet-600 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {acknowledgedCount > 0 && <button type="button" disabled={clearing} onClick={() => void clearHistory(true)} className="min-h-11 rounded-lg border border-gray-700 px-3 text-sm font-medium text-gray-200 hover:bg-gray-800 disabled:opacity-50">Clear acknowledged</button>}
          {triggers.length > 0 && <button type="button" disabled={clearing} onClick={() => void clearHistory(false)} className="min-h-11 rounded-lg border border-rose-900 px-3 text-sm font-medium text-rose-300 hover:bg-rose-950/60 disabled:opacity-50">Clear all</button>}
        </div>
      </div>
      {clearMessage && <p role="status" className="text-sm text-gray-300">{clearMessage}</p>}

      <div className="rounded-lg border border-gray-800 bg-gray-900">
        {visible.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            {filter === "unacked" && triggers.length > 0
              ? "All triggers are acknowledged."
              : "No triggers recorded yet."}
          </p>
        ) : (
          <div className="divide-y divide-gray-800">
            {visible.map((t) => (
              <div
                key={t.id}
                className="px-4 py-3 flex items-center justify-between gap-3"
              >
                <div className="flex flex-wrap items-center gap-3 min-w-0">
                  <span className="font-mono text-sm font-medium text-gray-200">
                    {t.symbol}
                  </span>
                  <span
                    className={`text-xs font-mono px-2 py-0.5 rounded ${
                      t.comparator.startsWith("pct_change")
                        ? "bg-violet-900/40 text-violet-300"
                        : t.comparator.startsWith("rsi")
                          ? "bg-blue-900/40 text-blue-300"
                          : t.comparator === "above" ||
                              t.comparator === "crosses_above"
                            ? "bg-green-900/40 text-green-400"
                            : "bg-red-900/40 text-red-400"
                    }`}
                  >
                    {comparatorLabel(t.comparator)} {t.current_value}
                    {valueSuffix(t.comparator)}
                    <span className="opacity-60">
                      {" "}
                      vs {t.threshold}
                      {valueSuffix(t.comparator)}
                    </span>
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400">
                    {t.interval}
                  </span>
                  {t.window_seconds != null && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-gray-800 text-gray-400">
                      {formatWindow(t.window_seconds)} window
                    </span>
                  )}
                  <span className="text-xs text-gray-500 whitespace-nowrap">
                    {new Date(t.triggered_at).toLocaleString()}
                  </span>
                </div>
                {t.acknowledged ? (
                  <span className="text-xs px-2 py-1 rounded-full bg-green-900/30 text-green-400 whitespace-nowrap">
                    Acknowledged
                  </span>
                ) : (
                  <button
                    onClick={() => ack(t.id)}
                    disabled={ackingId === t.id}
                    className="px-3 py-1 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded text-xs font-medium transition-colors whitespace-nowrap"
                  >
                    {ackingId === t.id ? "Acking..." : "Ack"}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
