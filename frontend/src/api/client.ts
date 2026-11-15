import type {
  AlertRule,
  AlertTemplate,
  AlertTrigger,
  Candle,
  IndicatorPoint,
  SymbolSummary,
} from "../types";

const GATEWAY = "/api";

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${GATEWAY}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ error: res.statusText }));
    throw new Error(body.error || `HTTP ${res.status}`);
  }
  return res.json();
}

function alertApi<T>(path: string, init?: RequestInit): Promise<T> {
  return api(path, init);
}

export const client = {
  health(): Promise<{ status: string }> {
    return api("/healthz");
  },

  alertHealth(): Promise<{ status: string }> {
    return api("/healthz/alert-service");
  },

  commandHealth(): Promise<{ status: string }> {
    return api("/healthz/command-service");
  },

  listSymbols(): Promise<{ symbols: string[] }> {
    return api("/v1/symbols");
  },

  searchSymbols(q = "", limit = 50): Promise<{ symbols: SymbolSummary[] }> {
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
    if (fromMs) p.set("from_ms", String(fromMs));
    if (toMs) p.set("to_ms", String(toMs));
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
    return api("/v1/watchlists", {
      method: "POST",
      body: JSON.stringify({ name, symbols }),
    });
  },

  createAlertRule(input: {
    symbol: string;
    comparator: string;
    threshold: number;
    interval?: string;
    window_seconds?: number | null;
    cooldown_seconds?: number;
  }): Promise<{ id: string }> {
    return api("/v1/alert-rules", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  listAlertTemplates(): Promise<AlertTemplate[]> {
    return api("/v1/alert-templates");
  },

  listAlertRules(tenantId?: string): Promise<AlertRule[]> {
    const p = tenantId ? `?tenant_id=${tenantId}` : "";
    return alertApi(`/v1/alert-rules${p}`);
  },

  getAlertRule(ruleId: string): Promise<AlertRule> {
    return alertApi(`/v1/alert-rules/${ruleId}`);
  },

  listTriggers(tenantId?: string, limit = 50): Promise<AlertTrigger[]> {
    const p = new URLSearchParams({ limit: String(limit) });
    if (tenantId) p.set("tenant_id", tenantId);
    return alertApi(`/v1/triggers?${p}`);
  },

  ackTrigger(triggerId: string): Promise<AlertTrigger> {
    return alertApi(`/v1/triggers/${triggerId}/ack`, { method: "POST" });
  },

  exportCandles(
    symbol: string,
    interval: string,
    format: "csv" | "json",
  ): Promise<Blob> {
    const p = new URLSearchParams({ symbol, interval, format });
    return fetch(`${GATEWAY}/v1/candles/export?${p}`).then((res) => {
      if (!res.ok) throw new Error(`Export failed: ${res.status}`);
      return res.blob();
    });
  },
};
