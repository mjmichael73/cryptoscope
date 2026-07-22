import { type FormEvent, useCallback, useEffect, useState } from "react";
import { client } from "../api/client";

interface WatchlistItem {
  id: string;
  name: string;
  symbols: string[];
}

export default function Watchlists() {
  const [watchlists, setWatchlists] = useState<WatchlistItem[]>([]);
  const [name, setName] = useState("");
  const [symbolsInput, setSymbolsInput] = useState("");
  const [symbolList, setSymbolList] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    client.listSymbols().then((r) => setSymbolList(r.symbols));
  }, []);

  const load = useCallback(async () => {
    try {
      const rules = await client.listAlertRules();
      const wls: WatchlistItem[] = rules
        .filter((r) => r.symbol)
        .reduce(
          (acc, r) => {
            const existing = acc.find((w) => w.name === r.status);
            if (existing) {
              if (!existing.symbols.includes(r.symbol))
                existing.symbols.push(r.symbol);
            } else {
              acc.push({
                id: r.id,
                name: `Watchlist (${r.status})`,
                symbols: [r.symbol],
              });
            }
            return acc;
          },
          [] as WatchlistItem[],
        );
      setWatchlists(wls);
    } catch {
      // silent
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      const sl = symbolsInput
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean);
      await client.createWatchlist(name.trim(), sl);
      setSuccess(`Watchlist "${name}" created`);
      setName("");
      setSymbolsInput("");
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
        <h2 className="text-xl font-bold">Watchlists</h2>
        <p className="text-sm text-gray-500 mt-1">
          Create and manage symbol watchlists
        </p>
      </div>

      <form
        onSubmit={handleSubmit}
        className="rounded-lg border border-gray-800 bg-gray-900 p-4 space-y-3"
      >
        <h3 className="text-sm font-medium text-gray-300">New Watchlist</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Name</label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Watchlist"
              required
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Symbols (comma-separated)
            </label>
            <input
              className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
              value={symbolsInput}
              onChange={(e) => setSymbolsInput(e.target.value)}
              placeholder="BTCUSDT,ETHUSDT"
            />
          </div>
        </div>
        {symbolList.length > 0 && (
          <div>
            <p className="text-xs text-gray-500 mb-1">
              Available symbols: {symbolList.join(", ")}
            </p>
          </div>
        )}
        <button
          type="submit"
          disabled={creating}
          className="px-4 py-1.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-50 rounded text-sm font-medium transition-colors"
        >
          {creating ? "Creating..." : "Create Watchlist"}
        </button>
        {error && <p className="text-sm text-red-400">{error}</p>}
        {success && <p className="text-sm text-green-400">{success}</p>}
      </form>

      <div className="space-y-3">
        {watchlists.length === 0 && (
          <p className="text-sm text-gray-500 text-center py-8">
            No watchlists yet. Create one above.
          </p>
        )}
        {watchlists.map((wl) => (
          <div
            key={wl.id}
            className="rounded-lg border border-gray-800 bg-gray-900 p-4"
          >
            <h3 className="text-sm font-medium text-gray-300 mb-2">{wl.name}</h3>
            <div className="flex flex-wrap gap-2">
              {wl.symbols.map((s) => (
                <span
                  key={s}
                  className="px-2.5 py-0.5 rounded-full bg-gray-800 text-gray-400 text-xs font-mono"
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
