import { type FormEvent, useCallback, useEffect, useState } from 'react';
import { client } from '../api/client';
import type { Watchlist } from '../types';

function parseSymbols(value: string): string[] {
  return value.split(',').map((symbol) => symbol.trim().toUpperCase()).filter(Boolean);
}

export default function Watchlists() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([]);
  const [name, setName] = useState('');
  const [symbolsInput, setSymbolsInput] = useState('');
  const [symbolList, setSymbolList] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [editSymbols, setEditSymbols] = useState('');
  const [savingId, setSavingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setWatchlists(await client.listWatchlists());
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not load watchlists');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    void client.listSymbols().then((result) => setSymbolList(result.symbols)).catch(() => setSymbolList([]));
  }, [load]);

  const handleCreate = async (event: FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      const submittedName = name.trim();
      await client.createWatchlist(submittedName, parseSymbols(symbolsInput));
      setSuccess(`Watchlist "${submittedName}" created`);
      setName('');
      setSymbolsInput('');
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Watchlist could not be created');
    } finally {
      setCreating(false);
    }
  };

  const beginEdit = (watchlist: Watchlist) => {
    setEditingId(watchlist.id);
    setEditName(watchlist.name);
    setEditSymbols(watchlist.symbols.join(', '));
    setError(null);
    setSuccess(null);
  };

  const saveEdit = async (watchlist: Watchlist) => {
    setSavingId(watchlist.id);
    setError(null);
    setSuccess(null);
    try {
      await client.updateWatchlist(watchlist.id, editName.trim(), parseSymbols(editSymbols));
      setSuccess(`Watchlist "${editName.trim()}" updated`);
      setEditingId(null);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Watchlist could not be updated');
    } finally {
      setSavingId(null);
    }
  };

  const remove = async (watchlist: Watchlist) => {
    if (!window.confirm(`Delete "${watchlist.name}"?`)) return;
    setError(null);
    setSuccess(null);
    try {
      await client.deleteWatchlist(watchlist.id);
      setSuccess(`Watchlist "${watchlist.name}" deleted`);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Watchlist could not be deleted');
    }
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <header>
        <h2 className="text-xl font-bold text-gray-100">Watchlists</h2>
        <p className="mt-1 text-sm text-gray-400">Create and manage symbol watchlists</p>
      </header>

      <form onSubmit={handleCreate} className="space-y-4 rounded-xl border border-gray-800 bg-gray-900 p-5">
        <h3 className="text-sm font-semibold text-gray-200">New Watchlist</h3>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="watchlist-name" className="mb-1.5 block text-sm text-gray-300">Name</label>
            <input id="watchlist-name" className="min-h-11 w-full rounded-lg border border-gray-700 bg-gray-800 px-3 text-sm text-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400" value={name} onChange={(event) => setName(event.target.value)} placeholder="My Watchlist" required />
          </div>
          <div>
            <label htmlFor="watchlist-symbols" className="mb-1.5 block text-sm text-gray-300">Symbols (comma-separated)</label>
            <input id="watchlist-symbols" className="min-h-11 w-full rounded-lg border border-gray-700 bg-gray-800 px-3 text-sm text-gray-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400" value={symbolsInput} onChange={(event) => setSymbolsInput(event.target.value)} placeholder="BTCUSDT, ETHUSDT" />
          </div>
        </div>
        {symbolList.length > 0 && <p className="text-xs text-gray-400">Available symbols: {symbolList.join(', ')}</p>}
        <button type="submit" disabled={creating} className="min-h-11 rounded-lg bg-violet-600 px-4 text-sm font-semibold text-white transition-colors hover:bg-violet-500 disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-300">
          {creating ? 'Creating…' : 'Create Watchlist'}
        </button>
      </form>

      {error && <p role="alert" className="rounded-lg border border-rose-900 bg-rose-950/50 px-4 py-3 text-sm text-rose-200">{error}</p>}
      {success && <p role="status" className="rounded-lg border border-emerald-900 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-200">{success}</p>}

      <section aria-label="Saved watchlists" className="space-y-3">
        {loading ? <p className="py-8 text-center text-sm text-gray-400">Loading watchlists…</p> : watchlists.length === 0 ? (
          <p className="rounded-xl border border-dashed border-gray-700 py-10 text-center text-sm text-gray-400">No watchlists yet. Create one above.</p>
        ) : watchlists.map((watchlist) => (
          <article key={watchlist.id} className="rounded-xl border border-gray-800 bg-gray-900 p-5">
            {editingId === watchlist.id ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <label htmlFor={`edit-name-${watchlist.id}`} className="mb-1.5 block text-sm text-gray-300">Name</label>
                    <input id={`edit-name-${watchlist.id}`} aria-label={`Edit name for ${watchlist.name}`} value={editName} onChange={(event) => setEditName(event.target.value)} className="min-h-11 w-full rounded-lg border border-gray-700 bg-gray-800 px-3 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400" />
                  </div>
                  <div>
                    <label htmlFor={`edit-symbols-${watchlist.id}`} className="mb-1.5 block text-sm text-gray-300">Symbols (comma-separated)</label>
                    <input id={`edit-symbols-${watchlist.id}`} aria-label={`Edit symbols for ${watchlist.name}`} value={editSymbols} onChange={(event) => setEditSymbols(event.target.value)} className="min-h-11 w-full rounded-lg border border-gray-700 bg-gray-800 px-3 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400" />
                  </div>
                </div>
                <div className="flex gap-2">
                  <button type="button" disabled={savingId === watchlist.id} onClick={() => void saveEdit(watchlist)} className="min-h-11 rounded-lg bg-violet-600 px-4 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-50">{savingId === watchlist.id ? 'Saving…' : 'Save changes'}</button>
                  <button type="button" onClick={() => setEditingId(null)} className="min-h-11 rounded-lg border border-gray-700 px-4 text-sm text-gray-300 hover:bg-gray-800">Cancel</button>
                </div>
              </div>
            ) : (
              <>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h3 className="text-base font-semibold text-gray-100">{watchlist.name}</h3>
                    {watchlist.created_at && <p className="mt-1 text-xs text-gray-400">Created {new Date(watchlist.created_at).toLocaleDateString()}</p>}
                  </div>
                  <div className="flex gap-2">
                    <button type="button" aria-label={`Edit ${watchlist.name}`} onClick={() => beginEdit(watchlist)} className="min-h-10 rounded-lg border border-gray-700 px-3 text-sm text-gray-200 hover:bg-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400">Edit</button>
                    <button type="button" aria-label={`Delete ${watchlist.name}`} onClick={() => void remove(watchlist)} className="min-h-10 rounded-lg border border-rose-900 px-3 text-sm text-rose-300 hover:bg-rose-950/60 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-400">Delete</button>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  {watchlist.symbols.map((symbol) => <span key={symbol} className="rounded-full bg-gray-800 px-3 py-1 font-mono text-xs text-gray-200">{symbol}</span>)}
                  {watchlist.symbols.length === 0 && <span className="text-sm text-gray-400">No symbols yet.</span>}
                </div>
              </>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
