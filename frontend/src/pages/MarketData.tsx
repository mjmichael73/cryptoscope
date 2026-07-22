import { useCallback, useEffect, useState } from "react";
import { client } from "../api/client";
import CandleChart from "../components/CandleChart";
import IndicatorChart from "../components/IndicatorChart";
import type { Candle, IndicatorPoint } from "../types";

const INTERVALS = ["1m", "5m", "1h", "1d"];
const INDICATOR_TYPES = [
  { value: "sma", label: "SMA", color: "#a78bfa" },
  { value: "ema", label: "EMA", color: "#f472b6" },
  { value: "volatility", label: "Volatility", color: "#fbbf24" },
];

export default function MarketData() {
  const [symbols, setSymbols] = useState<string[]>([]);
  const [symbol, setSymbol] = useState("BTCUSDT");
  const [interval_, setInterval_] = useState("1h");
  const [candles, setCandles] = useState<Candle[]>([]);
  const [loadingCandles, setLoadingCandles] = useState(false);
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
      setCandles(r.candles);
    } catch (e) {
      setError(e instanceof Error ? e.message : "failed to load candles");
    } finally {
      setLoadingCandles(false);
    }
  }, [symbol, interval_]);

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
      </div>

      {error && (
        <div className="rounded-lg border border-red-800 bg-red-900/20 p-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="rounded-lg border border-gray-800 bg-gray-900 p-4">
        <h3 className="text-sm font-medium text-gray-300 mb-3">
          Candles — {symbol} ({interval_})
        </h3>
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
