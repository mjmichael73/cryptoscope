import { type FormEvent, useCallback, useEffect, useState } from "react";
import { client } from "../api/client";
import type { AlertRule, AlertTemplate, Comparator } from "../types";

const COMPARATORS: { value: Comparator; label: string }[] = [
  { value: "above", label: "Above" },
  { value: "below", label: "Below" },
  { value: "crosses_above", label: "Crosses above" },
  { value: "crosses_below", label: "Crosses below" },
  { value: "pct_change_above", label: "Rally ≥ %" },
  { value: "pct_change_below", label: "Drop ≥ %" },
  { value: "rsi_above", label: "RSI above" },
  { value: "rsi_below", label: "RSI below" },
];

const INTERVALS = ["1m", "5m", "1h"];

function comparatorLabel(value: string): string {
  return COMPARATORS.find((c) => c.value === value)?.label ?? value;
}

function isPctChange(value: string): boolean {
  return value.startsWith("pct_change");
}

export default function AlertRules() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [templates, setTemplates] = useState<AlertTemplate[]>([]);
  const [templateId, setTemplateId] = useState("");
  const [symbol, setSymbol] = useState("");
  const [comparator, setComparator] = useState<Comparator>("above");
  const [threshold, setThreshold] = useState("");
  const [interval_, setInterval_] = useState("1m");
  const [windowSeconds, setWindowSeconds] = useState("3600");
  const [symbolList, setSymbolList] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    client.listSymbols().then((r) => {
      setSymbolList(r.symbols);
      if (r.symbols.length > 0) setSymbol(r.symbols[0]);
    });
    client
      .listAlertTemplates()
      .then(setTemplates)
      .catch(() => {
        // templates are optional; the form still works without them
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

  const applyTemplate = (id: string) => {
    setTemplateId(id);
    const template = templates.find((t) => t.id === id);
    if (!template) return;
    setComparator(template.comparator);
    setInterval_(template.interval);
    if (template.window_seconds != null) {
      setWindowSeconds(String(template.window_seconds));
    }
    setThreshold(template.threshold != null ? String(template.threshold) : "");
  };

  const removeRule = async (rule: AlertRule) => {
    if (!window.confirm(`Delete alert rule for ${rule.symbol}?`)) return;
    setDeletingId(rule.id);
    setError(null);
    setSuccess(null);
    try {
      await client.deleteAlertRule(rule.id);
      setSuccess(`Alert rule for ${rule.symbol} deleted`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Rule could not be deleted');
    } finally {
      setDeletingId(null);
    }
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!symbol || !threshold) return;
    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      const value = parseFloat(threshold);
      if (isNaN(value)) {
        setError("Invalid threshold");
        return;
      }
      const template = templates.find((t) => t.id === templateId);
      await client.createAlertRule({
        symbol,
        comparator,
        threshold: value,
        interval: interval_,
        window_seconds: isPctChange(comparator) ? parseInt(windowSeconds, 10) : null,
        cooldown_seconds: template?.cooldown_seconds ?? 300,
      });
      setSuccess(
        `Rule created: ${symbol} ${comparatorLabel(comparator)} ${value} (${interval_})`,
      );
      setThreshold("");
      setTemplateId("");
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
          Configure price, movement and RSI alert rules
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-gray-800 bg-gray-900 p-4 space-y-3"
      >
        <h3 className="text-sm font-medium text-gray-300">New Alert Rule</h3>

        {templates.length > 0 && (
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Template (optional)
            </label>
            <select
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              value={templateId}
              onChange={(e) => applyTemplate(e.target.value)}
            >
              <option value="">Custom rule</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            {templateId && (
              <p className="text-xs text-gray-500 mt-1">
                {templates.find((t) => t.id === templateId)?.description}
              </p>
            )}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-5 gap-3">
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
              onChange={(e) => setComparator(e.target.value as Comparator)}
            >
              {COMPARATORS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Interval
            </label>
            <select
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              value={interval_}
              onChange={(e) => setInterval_(e.target.value)}
            >
              {INTERVALS.map((iv) => (
                <option key={iv} value={iv}>
                  {iv}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              {isPctChange(comparator) ? "Threshold (%)" : "Threshold"}
            </label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              type="number"
              step="any"
              value={threshold}
              onChange={(e) => setThreshold(e.target.value)}
              placeholder={isPctChange(comparator) ? "5.0" : "10000.0"}
              required
            />
          </div>
          <div className={isPctChange(comparator) ? "" : "opacity-40"}>
            <label className="block text-xs text-gray-500 mb-1">
              Window (s)
            </label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              type="number"
              value={windowSeconds}
              onChange={(e) => setWindowSeconds(e.target.value)}
              disabled={!isPctChange(comparator)}
              min={60}
              max={86400}
            />
          </div>
          <div className="flex items-end sm:col-span-5">
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded text-sm font-medium transition-colors"
            >
              {creating ? "Creating..." : "Create Rule"}
            </button>
          </div>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        {success && <p className="text-sm text-green-400">{success}</p>}
      </form>

      <section className="overflow-hidden rounded-xl border border-gray-800 bg-gray-900">
        <div className="border-b border-gray-800 px-4 py-3">
          <h3 className="text-sm font-medium text-gray-200">All Rules ({rules.length})</h3>
        </div>
        {rules.length === 0 ? (
          <p className="py-8 text-center text-sm text-gray-400">No alert rules configured.</p>
        ) : (
          <div className="overflow-x-auto">
            <table aria-label="Alert rules" className="w-full min-w-[760px] text-left text-sm">
              <thead className="bg-gray-800/60 text-xs uppercase tracking-wide text-gray-400">
                <tr>
                  <th scope="col" className="px-4 py-3">Symbol</th>
                  <th scope="col" className="px-4 py-3">Comparator</th>
                  <th scope="col" className="px-4 py-3">Threshold</th>
                  <th scope="col" className="px-4 py-3">Interval</th>
                  <th scope="col" className="px-4 py-3">Status</th>
                  <th scope="col" className="px-4 py-3">Created</th>
                  <th scope="col" className="px-4 py-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800">
                {rules.map((rule) => (
                  <tr key={rule.id}>
                    <td className="whitespace-nowrap px-4 py-3 font-mono font-medium text-gray-100">{rule.symbol}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-300">{comparatorLabel(rule.comparator)}</td>
                    <td className="whitespace-nowrap px-4 py-3 font-mono text-gray-200">{rule.threshold}{rule.comparator.startsWith('pct_change') ? '%' : ''}</td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-300">{rule.interval}</td>
                    <td className="px-4 py-3"><span className={`rounded-full px-2.5 py-1 text-xs ${rule.status === 'active' ? 'bg-emerald-900/40 text-emerald-300' : rule.status === 'paused' ? 'bg-amber-900/40 text-amber-300' : 'bg-gray-800 text-gray-300'}`}>{rule.status}</span></td>
                    <td className="whitespace-nowrap px-4 py-3 text-gray-400">{new Date(rule.created_at).toLocaleDateString()}</td>
                    <td className="px-4 py-3"><button type="button" aria-label={`Delete rule for ${rule.symbol}`} disabled={deletingId === rule.id} onClick={() => void removeRule(rule)} className="min-h-10 rounded-lg border border-rose-900 px-3 text-xs font-medium text-rose-300 hover:bg-rose-950/60 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-400">{deletingId === rule.id ? 'Deleting…' : 'Delete'}</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
