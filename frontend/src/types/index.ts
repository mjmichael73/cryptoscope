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

export interface AlertRule {
  id: string;
  tenant_id: string;
  symbol: string;
  comparator: "above" | "below";
  threshold: number;
  status: string;
  created_at: string;
  updated_at: string;
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
}

export interface Watchlist {
  id: string;
  name: string;
  symbols: string[];
  created_at?: string;
}
