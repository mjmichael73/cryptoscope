import { useCallback, useEffect, useState } from "react";
import { client } from "../api/client";
import CandleChart from "../components/CandleChart";
import IndicatorChart from "../components/IndicatorChart";
import { downloadBlob, useCandleStream } from "../hooks/useCandleStream";
import type { Candle, IndicatorPoint } from "../types";

const INTERVALS = ["1m", "5m", "1h", "1d"];
const INDICATOR_TYPES = [
  { value: "sma", label: "SMA", color: "#a78bfa" },
  { value: "ema", label: "EMA", color: "#f472b6" },
  { value: "volatility", label: "Volatility", color: "#fbbf24" },
  { value: "rsi", label: "RSI", color: "#e879f9" },
  { value: "macd", label: "MACD", color: "#34d399" },
  { value: "macd_signal", label: "MACD Signal", color: "#22d3ee" },
  { value: "macd_histogram", label: "MACD Hist", color: "#60a5fa" },
  { value: "bb_upper", label: "BB Upper", color: "#f87171" },
  { value: "bb_middle", label: "BB Middle", color: "#94a3b8" },
  { value: "bb_lower", label: "BB Lower", color: "#fb923c" },
];

export default function MarketData() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [interval_, setInterval_] = useState("1h");
  const [loadingCandles, setLoadingCandles] = useState(false);
  const [initialCandles, setInitialCandles] = useState<Candle[]>([]);
  const { candles, connected, reconnects } = useCandleStream(symbol, interval_, initialCandles);
  const [indicators, setIndicators] = useState<
    { type: string; points: IndicatorPoint[]; color: string }[]
  >([]);
  const [loadingIndicators, setLoadingIndicators] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    client.listSymbols().then((r) => {
      setSymbols(r.symbols);
      if (r.symbols.length > 0) setSymbol(r.symbols[0]);
    });
  }, []);

  const loadCandles = useCallback(async () => {
    setLoadingCandles(true);
    setError(null);
    try {
      const r = await client.getCandles(symbol, interval_);
      setInitialCandles(r.candles);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load candles");
    } finally {
      setLoadingCandles(false);
    }
  }, [symbol, interval_]);

  const handleExport = useCallback(
    async (format: "csv" | "json") => {
      try {
        const blob = await client.exportCandles(symbol, interval_, format);
        downloadBlob(blob, `${symbol}_${interval_}_candles.${format}`);
      } catch (e) {
        setError(e instanceof Error ? e.message : "failed to export");
      }
    },
    [symbol, interval_],
  );

  const loadIndicators = useCallback(async () => {
    setLoadingIndicators(true);
    try {
      const results = await Promise.all(
        INDICATOR_TYPES.map((it) =>
          client.getIndicator(symbol, it.value, interval_, 14),
        ),
      );
      setIndicators(
        results.map((r, i) => ({
          type: INDICATOR_TYPES[i].label,
          points: r.points,
          color: INDICATOR_TYPES[i].color,
        })),
      );
    } catch {
      // partial failure is fine
    } finally {
      setLoadingIndicators(false);
    }
  }, [symbol, interval_]);

  useEffect(() => {
    if (symbol) {
      loadCandles();
      loadIndicators();
    }
  }, [loadCandles, loadIndicators, symbol, interval_]);

  return (
    <div className="space-y-6 max-w-6xl">
      <div>
        <h2 className="text-xl font-bold">Market Data</h2>
        <p className="text-sm text-gray-500 mt-1">
          Candlestick chart and technical indicators
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Symbol</label>
          <select
            className="bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
          >
            {symbols.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Interval</label>
          <div className="flex gap-1">
            {INTERVALS.map((iv) => (
              <button
                key={iv}
                onClick={() => setInterval_(iv)}
                className={`px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                  interval_ === iv
                    ? "bg-violet-600 text-white"
                    : "bg-gray-800 text-gray-400 hover:bg-gray-700"
                }`}
              >
                {iv}
              </button>
            ))}
          </div>
        </div>
        <div className="ml-auto flex items-end gap-1">
          <button
            onClick={() => handleExport("csv")}
            className="px-3 py-1.5 rounded text-xs font-medium bg-gray-800 text-gray-400 hover:bg-gray-700 transition-colors"
          >
            Export CSV
          </button>
          <button
            onClick={() => handleExport("json")}
            className="px-3 py-1.5 rounded text-xs font-medium bg-gray-800 text-gray-400 hover:bg-gray-700 transition-colors"
          >
            Export JSON
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium text-gray-300">
            Candles — {symbol} ({interval_})
          </h3>
          <span
            aria-live="polite"
            className={`rounded-full px-2.5 py-1 text-xs ${
              connected
                ? "bg-green-900/40 text-green-300"
                : reconnects > 0
                  ? "bg-amber-900/40 text-amber-300"
                  : "bg-gray-800 text-gray-400"
            }`}
          >
            {connected ? "Live" : reconnects > 0 ? `Reconnecting · ${reconnects}` : "Offline"}
          </span>
        </div>
        {loadingCandles ? (
          <div className="flex h-64 items-center justify-center text-gray-500">
            Loading...
          </div>
        ) : (
          <CandleChart candles={candles} />
        )}
      </div>

      {indicators.map((ind) => (
        <div
          key={ind.type}
          className="rounded-lg border border-gray-800 bg-gray-900 p-4"
        >
          <h3 className="text-sm font-medium text-gray-300 mb-3">
            {ind.type} (14) — {symbol} ({interval_})
          </h3>
          {loadingIndicators ? (
            <div className="flex h-48 items-center justify-center text-gray-500">
              Loading...
            </div>
          ) : (
            <IndicatorChart points={ind.points} color={ind.color} />
          )}
        </div>
      ))}
    </div>
  );
}
