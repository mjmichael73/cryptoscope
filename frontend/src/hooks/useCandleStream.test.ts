import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCandleStream } from './useCandleStream';

class FakeEventSource extends EventTarget {
  static instances: FakeEventSource[] = [];
  onerror: ((event: Event) => void) | null = null;
  closed = false;
  constructor(readonly url: string) {
    super();
    FakeEventSource.instances.push(this);
  }
  close() { this.closed = true; }
  connect() { this.dispatchEvent(new Event('connected')); }
  fail() { this.onerror?.(new Event('error')); }
}

beforeEach(() => {
  vi.useFakeTimers();
  vi.spyOn(Math, 'random').mockReturnValue(0.5);
  FakeEventSource.instances = [];
  vi.stubGlobal('EventSource', FakeEventSource);
});
afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

const emptyCandles: import('../types').Candle[] = [];
const renderStream = () => renderHook(() => useCandleStream('BTCUSDT', '1m', emptyCandles));

describe('useCandleStream reconnect', () => {
  it('reconnects after the first one-second delay', () => {
    const { result } = renderStream();
    expect(FakeEventSource.instances).toHaveLength(1);
    act(() => FakeEventSource.instances[0].fail());
    expect(result.current.reconnects).toBe(1);
    expect(result.current.connected).toBe(false);
    act(() => vi.advanceTimersByTime(999));
    expect(FakeEventSource.instances).toHaveLength(1);
    act(() => vi.advanceTimersByTime(1));
    expect(FakeEventSource.instances).toHaveLength(2);
  });

  it('increases the delay exponentially and caps it at thirty seconds', () => {
    renderStream();
    const delays = [1000, 2000, 4000, 8000, 16000, 30000];
    for (const delay of delays) {
      const current = FakeEventSource.instances.at(-1)!;
      act(() => current.fail());
      act(() => vi.advanceTimersByTime(delay));
      expect(FakeEventSource.instances.length).toBeGreaterThan(delays.indexOf(delay) + 1);
    }
    expect(FakeEventSource.instances).toHaveLength(7);
  });

  it('resets backoff after a successful connected event', () => {
    renderStream();
    act(() => FakeEventSource.instances[0].fail());
    act(() => vi.advanceTimersByTime(1000));
    act(() => FakeEventSource.instances[1].connect());
    act(() => FakeEventSource.instances[1].fail());
    act(() => vi.advanceTimersByTime(999));
    expect(FakeEventSource.instances).toHaveLength(2);
    act(() => vi.advanceTimersByTime(1));
    expect(FakeEventSource.instances).toHaveLength(3);
  });

  it('cancels a scheduled reconnect on unmount', () => {
    const { unmount } = renderStream();
    act(() => FakeEventSource.instances[0].fail());
    unmount();
    act(() => vi.advanceTimersByTime(2000));
    expect(FakeEventSource.instances).toHaveLength(1);
    expect(FakeEventSource.instances[0].closed).toBe(true);
  });
});
