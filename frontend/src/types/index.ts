export interface Candle {
  open_time_ms: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface IndicatorPoint {
  time_ms: number;
  value: number;
}

export type Comparator =
  | "above"
  | "below"
  | "crosses_above"
  | "crosses_below"
  | "pct_change_above"
  | "pct_change_below"
  | "rsi_above"
  | "rsi_below";

export interface AlertRule {
  id: string;
  tenant_id: string;
  symbol: string;
  comparator: Comparator;
  threshold: number;
  status: string;
  created_at: string;
  updated_at: string;
  interval: string;
  window_seconds: number | null;
  cooldown_seconds: number;
}

export interface AlertTrigger {
  id: string;
  tenant_id: string;
  rule_id: string;
  symbol: string;
  comparator: string;
  threshold: number;
  current_value: number;
  triggered_at: string;
  acknowledged: boolean;
  interval: string;
  window_seconds: number | null;
}

export interface AlertTemplate {
  id: string;
  name: string;
  description: string;
  comparator: Comparator;
  threshold: number | null;
  window_seconds: number | null;
  interval: string;
  cooldown_seconds: number;
}

export interface Watchlist {
  id: string;
  name: string;
  symbols: string[];
  created_at?: string;
}
