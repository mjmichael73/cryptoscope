import { useCallback, useEffect, useState } from "react";
import { client } from "../api/client";
import type { AlertTrigger } from "../types";

export default function AlertTriggers() {
  const [triggers, setTriggers] = useState<AlertTrigger[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setTriggers(await client.listTriggers());
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-500">
        Loading...
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h2 className="text-xl font-bold">Alert Triggers</h2>
        <p className="text-sm text-gray-500 mt-1">
          History of triggered alert events
        </p>
      </div>

      <div className="rounded-lg border border-gray-800 bg-gray-900">
        <div className="px-4 py-3 border-b border-gray-800">
          <h3 className="text-sm font-medium text-gray-300">
            Recent Triggers ({triggers.length})
          </h3>
        </div>
        {triggers.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-8">
            No triggers yet.
          </p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-left text-xs text-gray-500 uppercase">
                <th className="px-4 py-2 font-medium">Symbol</th>
                <th className="px-4 py-2 font-medium">Condition</th>
                <th className="px-4 py-2 font-medium">Actual Value</th>
                <th className="px-4 py-2 font-medium">Triggered At</th>
                <th className="px-4 py-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-800">
              {triggers.map((t) => (
                <tr key={t.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-4 py-3 font-mono font-medium text-gray-200">
                    {t.symbol}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs font-mono px-2 py-0.5 rounded ${
                        t.comparator === "above"
                          ? "bg-green-900/40 text-green-400"
                          : "bg-red-900/40 text-red-400"
                      }`}
                    >
                      {t.comparator} {t.threshold}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono">{t.current_value.toFixed(2)}</td>
                  <td className="px-4 py-3 text-gray-400 text-xs">
                    {new Date(t.triggered_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        t.acknowledged
                          ? "bg-gray-800 text-gray-500"
                          : "bg-amber-900/30 text-amber-400"
                      }`}
                    >
                      {t.acknowledged ? "Acknowledged" : "Pending"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
