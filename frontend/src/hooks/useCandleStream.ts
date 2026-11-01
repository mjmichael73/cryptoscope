import { useEffect, useRef, useState } from "react";
import type { Candle } from "../types";

const GATEWAY = "/api";

/**
 * Hook that connects to the SSE candle stream and returns the latest candles
 * as they arrive. Merges incoming candles with any already-loaded candles,
 * deduplicating by open_time_ms.
 */
export function useCandleStream(
  symbol: string,
  interval: string,
  initialCandles: Candle[],
): { candles: Candle[]; connected: boolean } {
  const [candles, setCandles] = useState<Candle[]>(initialCandles);
  const [connected, setConnected] = useState(false);
  const seenRef = useRef<Set<number>>(new Set());

  // Reset when symbol or interval changes.
  useEffect(() => {
    setCandles(initialCandles);
    seenRef.current = new Set(initialCandles.map((c) => c.open_time_ms));
  }, [symbol, interval, initialCandles]);

  useEffect(() => {
    const es = new EventSource(`${GATEWAY}/v1/candles/stream`);

    es.addEventListener("connected", () => {
      setConnected(true);
    });

    es.addEventListener("candle", (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        if (data.interval !== interval) return;

        const candle: Candle = {
          open_time_ms: data.open_time_ms,
          open: data.open,
          high: data.high,
          low: data.low,
          close: data.close,
          volume: data.volume,
        };

        setCandles((prev) => {
          if (seenRef.current.has(candle.open_time_ms)) {
            // Update existing candle (price may have changed).
            return prev.map((c) =>
              c.open_time_ms === candle.open_time_ms ? candle : c,
            );
          }
          seenRef.current.add(candle.open_time_ms);
          const next = [...prev, candle].sort(
            (a, b) => a.open_time_ms - b.open_time_ms,
          );
          // Keep at most 500 candles in memory.
          if (next.length > 500) next.splice(0, next.length - 500);
          return next;
        });
      } catch {
        // Ignore malformed events.
      }
    });

    es.onerror = () => {
      setConnected(false);
    };

    return () => {
      es.close();
      setConnected(false);
    };
  }, [interval]);

  return { candles, connected };
}

/**
 * Downloads a blob and triggers a file save in the browser.
 */
export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
