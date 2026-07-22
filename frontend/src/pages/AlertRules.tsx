import { type FormEvent, useCallback, useEffect, useState } from "react";
import { client } from "../api/client";
import type { AlertRule } from "../types";

export default function AlertRules() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [symbol, setSymbol] = useState("");
  const [comparator, setComparator] = useState<"above" | "below">("above");
  const [threshold, setThreshold] = useState("");
  const [symbolList, setSymbolList] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    client.listSymbols().then((r) => {
      setSymbolList(r.symbols);
      if (r.symbols.length > 0) setSymbol(r.symbols[0]);
    });
  }, []);

  const load = useCallback(async () => {
    try {
      setRules(await client.listAlertRules());
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!symbol || !threshold) return;
    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      const t = parseFloat(threshold);
      if (isNaN(t)) {
        setError("Invalid threshold");
        return;
      }
      await client.createAlertRule(symbol, comparator, t);
      setSuccess(`Rule created: ${symbol} ${comparator} ${t}`);
      setThreshold("");
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "creation failed");
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-bold">Alert Rules</h2>
        <p className="text-sm text-gray-500 mt-1">
          Configure price alert rules
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-gray-800 bg-gray-900 p-4 space-y-3"
      >
        <h3 className="text-sm font-medium text-gray-300">New Alert Rule</h3>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Symbol</label>
            <select
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
            >
              {symbolList.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Comparator
            </label>
            <select
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              value={comparator}
              onChange={(e) =>
                setComparator(e.target.value as "above" | "below")
              }
            >
              <option value="above">Above</option>
              <option value="below">Below</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Threshold
            </label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              type="number"
              step="any"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              placeholder="10000.0"
              required
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={creating}
              className="w-full px-4 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded text-sm font-medium transition-colors"
            >
              {creating ? "Creating..." : "Create Rule"}
            </button>
          </div>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        {success && <p className="text-sm text-green-400">{success}</p>}
      </form>

      <div className="rounded-lg border border-gray-800 bg-gray-900">
        <div className="px-4 py-3 border-b border-gray-800">
          <h3 className="text-sm font-medium text-gray-300">
            All Rules ({rules.length})
          </h3>
        </div>
        {rules.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            No alert rules configured.
          </p>
        ) : (
          <div className="divide-y divide-gray-800">
            {rules.map((r) => (
              <div key={r.id} className="px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <span className="font-mono text-sm font-medium text-gray-200">
                    {r.symbol}
                  </span>
                  <span
                    className={`text-xs font-mono px-2 py-0.5 rounded ${
                      r.comparator === "above"
                        ? "bg-green-900/40 text-green-400"
                        : "bg-red-900/40 text-red-400"
                    }`}
                  >
                    {r.comparator} {r.threshold}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      r.status === "active"
                        ? "bg-green-900/30 text-green-400"
                        : r.status === "paused"
                          ? "bg-yellow-900/30 text-yellow-400"
                          : "bg-gray-800 text-gray-500"
                    }`}
                  >
                    {r.status}
                  </span>
                </div>
                <span className="text-xs text-gray-500">
                  {new Date(r.created_at).toLocaleDateString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
