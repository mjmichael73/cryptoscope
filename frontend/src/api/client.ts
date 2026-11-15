import { clearSession, loadSession, saveSession } from '../auth/storage';
import { oidcConfigFromEnv, refreshToken } from '../auth/oidc';
import type {
  AlertRule,
  AlertTemplate,
  AlertTrigger,
  Candle,
  IndicatorPoint,
  SymbolSummary,
  Watchlist,
} from '../types';

const GATEWAY = '/api';

function expireAuth(): void {
  clearSession();
  window.dispatchEvent(new Event('cryptoscope:auth-expired'));
}

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method ?? 'GET').toUpperCase();
  const headers = new Headers({ 'Content-Type': 'application/json' });
  new Headers(init?.headers).forEach((value, key) => headers.set(key, value));
  const session = loadSession();
  if (session) headers.set('Authorization', `Bearer ${session.accessToken}`);
  if (method !== 'GET' && !headers.has('Idempotency-Key')) {
    headers.set('Idempotency-Key', crypto.randomUUID());
  }

  const request = () => fetch(`${GATEWAY}${path}`, { ...init, method, headers });
  let response = await request();
  if (response.status === 401) {
    if (!session?.refreshToken) {
      expireAuth();
    } else {
      try {
        const refreshed = await refreshToken(oidcConfigFromEnv(), session.refreshToken);
        const next = {
          ...session,
          accessToken: refreshed.access_token,
          refreshToken: refreshed.refresh_token ?? session.refreshToken,
          expiresAt: Date.now() + refreshed.expires_in * 1000,
          idToken: refreshed.id_token ?? session.idToken,
        };
        saveSession(next);
        headers.set('Authorization', `Bearer ${next.accessToken}`);
        response = await request();
        if (response.status === 401) expireAuth();
      } catch {
        expireAuth();
      }
    }
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(body.error || `HTTP ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function alertApi<T>(path: string, init?: RequestInit): Promise<T> {
  return api(path, init);
}

export const client = {
  health(): Promise<{ status: string }> {
    return api('/healthz');
  },

  alertHealth(): Promise<{ status: string }> {
    return api('/healthz/alert-service');
  },

  commandHealth(): Promise<{ status: string }> {
    return api('/healthz/command-service');
  },

  listSymbols(): Promise<{ symbols: string[] }> {
    return api('/v1/symbols');
  },

  searchSymbols(q = '', limit = 50): Promise<{ symbols: SymbolSummary[] }> {
    const p = new URLSearchParams({ q, limit: String(limit) });
    return api(`/v1/symbols/search?${p}`);
  },

  getCandles(
    symbol: string,
    interval: string,
    fromMs?: number,
    toMs?: number,
  ): Promise<{ candles: Candle[] }> {
    const p = new URLSearchParams({ symbol, interval });
    if (fromMs) p.set('from_ms', String(fromMs));
    if (toMs) p.set('to_ms', String(toMs));
    return api(`/v1/candles?${p}`);
  },

  getIndicator(
    symbol: string,
    type: string,
    interval: string,
    period: number,
  ): Promise<{ points: IndicatorPoint[] }> {
    const p = new URLSearchParams({ symbol, type, interval, period: String(period) });
    return api(`/v1/indicators?${p}`);
  },

  createWatchlist(name: string, symbols: string[]): Promise<{ id: string }> {
    return api('/v1/watchlists', {
      method: 'POST',
      body: JSON.stringify({ name, symbols }),
    });
  },

  listWatchlists(): Promise<Watchlist[]> {
    return api('/v1/watchlists');
  },

  getWatchlist(id: string): Promise<Watchlist> {
    return api(`/v1/watchlists/${encodeURIComponent(id)}`);
  },

  updateWatchlist(id: string, name: string, symbols: string[]): Promise<Watchlist> {
    return api(`/v1/watchlists/${encodeURIComponent(id)}`, {
      method: 'PUT',
      body: JSON.stringify({ name, symbols }),
    });
  },

  deleteWatchlist(id: string): Promise<void> {
    return api(`/v1/watchlists/${encodeURIComponent(id)}`, { method: 'DELETE' });
  },

  createAlertRule(input: {
    symbol: string;
    comparator: string;
    threshold: number;
    interval?: string;
    window_seconds?: number | null;
    cooldown_seconds?: number;
  }): Promise<{ id: string }> {
    return api('/v1/alert-rules', {
      method: 'POST',
      body: JSON.stringify(input),
    });
  },

  listAlertTemplates(): Promise<AlertTemplate[]> {
    return api('/v1/alert-templates');
  },

  listAlertRules(tenantId?: string): Promise<AlertRule[]> {
    const p = tenantId ? `?tenant_id=${encodeURIComponent(tenantId)}` : '';
    return alertApi(`/v1/alert-rules${p}`);
  },

  getAlertRule(ruleId: string): Promise<AlertRule> {
    return alertApi(`/v1/alert-rules/${encodeURIComponent(ruleId)}`);
  },

  deleteAlertRule(ruleId: string): Promise<void> {
    return alertApi(`/v1/alert-rules/${encodeURIComponent(ruleId)}`, { method: 'DELETE' });
  },

  listTriggers(tenantId?: string, limit = 50): Promise<AlertTrigger[]> {
    const p = new URLSearchParams({ limit: String(limit) });
    if (tenantId) p.set('tenant_id', tenantId);
    return alertApi(`/v1/triggers?${p}`);
  },

  clearTriggers(acknowledgedOnly: boolean): Promise<{ deleted: number }> {
    return alertApi(`/v1/triggers?acknowledged_only=${acknowledgedOnly}`, { method: 'DELETE' });
  },

  ackTrigger(triggerId: string): Promise<AlertTrigger> {
    return alertApi(`/v1/triggers/${encodeURIComponent(triggerId)}/ack`, { method: 'POST' });
  },

  exportCandles(
    symbol: string,
    interval: string,
    format: 'csv' | 'json',
  ): Promise<Blob> {
    const p = new URLSearchParams({ symbol, interval, format });
    const headers = new Headers();
    const session = loadSession();
    if (session) headers.set('Authorization', `Bearer ${session.accessToken}`);
    return fetch(`${GATEWAY}/v1/candles/export?${p}`, { headers }).then((res) => {
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      return res.blob();
    });
  },
};
