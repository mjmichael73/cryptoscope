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
): { candles: Candle[]; connected: boolean; reconnects: number } {
  const [candles, setCandles] = useState<Candle[]>(initialCandles);
  const [connected, setConnected] = useState(false);
  const [reconnects, setReconnects] = useState(0);
  const seenRef = useRef<Set<number>>(new Set());

  // Reset when symbol or interval changes.
  useEffect(() => {
    setCandles(initialCandles);
    seenRef.current = new Set(initialCandles.map((c) => c.open_time_ms));
  }, [symbol, interval, initialCandles]);

  useEffect(() => {
    let source: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let attempt = 0;
    let disposed = false;

    const connect = () => {
      if (disposed) return;
      reconnectTimer = undefined;
      const current = new EventSource(`${GATEWAY}/v1/candles/stream`);
      source = current;

      current.addEventListener('connected', () => {
        attempt = 0;
        setConnected(true);
      });

      current.addEventListener('candle', (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data.interval !== interval) return;

          const candle: Candle = {
            open_time_ms: data.open_time_ms,
            open: data.open,
            high: data.high,
            low: data.low,
            close: data.close,
            volume: data.volume,
          };

          setCandles((previous) => {
            if (seenRef.current.has(candle.open_time_ms)) {
              return previous.map((existing) =>
                existing.open_time_ms === candle.open_time_ms ? candle : existing,
              );
            }
            seenRef.current.add(candle.open_time_ms);
            const next = [...previous, candle].sort((a, b) => a.open_time_ms - b.open_time_ms);
            if (next.length > 500) next.splice(0, next.length - 500);
            return next;
          });
        } catch {
          // Ignore malformed events.
        }
      });

      current.onerror = () => {
        if (disposed || source !== current || reconnectTimer !== undefined) return;
        current.close();
        setConnected(false);
        const baseDelay = Math.min(1000 * 2 ** attempt, 30_000);
        const jitteredDelay = Math.round(baseDelay * (0.8 + Math.random() * 0.4));
        const delay = Math.min(30_000, jitteredDelay);
        attempt += 1;
        setReconnects((count) => count + 1);
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    setReconnects(0);
    connect();
    return () => {
      disposed = true;
      if (reconnectTimer !== undefined) clearTimeout(reconnectTimer);
      source?.close();
      setConnected(false);
    };
  }, [symbol, interval]);

  return { candles, connected, reconnects };
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
