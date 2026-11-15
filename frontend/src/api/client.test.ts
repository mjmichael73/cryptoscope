import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { client } from './client';
import { clearSession, saveSession } from '../auth/storage';

const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

beforeEach(() => {
  sessionStorage.clear();
  clearSession();
  vi.stubGlobal('fetch', vi.fn());
  vi.stubGlobal('crypto', { randomUUID: () => 'uuid-1' });
});
afterEach(() => vi.unstubAllGlobals());

describe('API client auth and management methods', () => {
  it('adds bearer and idempotency headers to a create request', async () => {
    saveSession({ accessToken: 'token-a', refreshToken: null, expiresAt: Date.now() + 60_000, idToken: null, username: 'mira' });
    vi.mocked(fetch).mockResolvedValue(response({ id: 'wl-1' }));
    await client.createWatchlist('Main', ['BTCUSDT']);
    const [, init] = vi.mocked(fetch).mock.calls[0];
    const headers = new Headers(init?.headers);
    expect(headers.get('Authorization')).toBe('Bearer token-a');
    expect(headers.get('Idempotency-Key')).toBe('uuid-1');
  });

  it('does not send an idempotency key on GET requests', async () => {
    vi.mocked(fetch).mockResolvedValue(response({ symbols: [] }));
    await client.listSymbols();
    const [, init] = vi.mocked(fetch).mock.calls[0];
    expect(new Headers(init?.headers).has('Idempotency-Key')).toBe(false);
  });

  it('refreshes once on 401 and retries with the new access token', async () => {
    saveSession({ accessToken: 'expired', refreshToken: 'refresh-me', expiresAt: Date.now() - 1000, idToken: null, username: 'mira' });
    const fetchMock = vi.mocked(fetch);
    fetchMock.mockResolvedValueOnce(response({ error: 'expired' }, 401)).mockResolvedValueOnce(response({ access_token: 'new-token', refresh_token: 'rotated', expires_in: 120 })).mockResolvedValueOnce(response({ symbols: ['BTCUSDT'] }));
    await expect(client.listSymbols()).resolves.toEqual({ symbols: ['BTCUSDT'] });
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(new Headers(fetchMock.mock.calls[2][1]?.headers).get('Authorization')).toBe('Bearer new-token');
  });

  it('clears session and signals login when refresh fails', async () => {
    saveSession({ accessToken: 'expired', refreshToken: 'dead', expiresAt: Date.now() - 1000, idToken: null, username: 'mira' });
    vi.mocked(fetch).mockResolvedValue(response({ error: 'expired' }, 401));
    const expired = vi.fn();
    window.addEventListener('cryptoscope:auth-expired', expired);
    await expect(client.listSymbols()).rejects.toThrow();
    expect(sessionStorage.getItem('cryptoscope.auth.access_token')).toBeNull();
    expect(expired).toHaveBeenCalledTimes(1);
    window.removeEventListener('cryptoscope:auth-expired', expired);
  });

  it('calls the new management endpoints with expected methods and payloads', async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(response([]))
      .mockResolvedValueOnce(response({ id: 'wl-1' }))
      .mockResolvedValueOnce(response({ id: 'wl-1' }))
      .mockResolvedValueOnce(response({ deleted: 2 }))
      .mockResolvedValueOnce(response({ deleted: 1 }))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    await client.listWatchlists();
    await client.getWatchlist('wl-1');
    await client.updateWatchlist('wl-1', 'New name', ['ETHUSDT']);
    await client.clearTriggers(true);
    await client.deleteAlertRule('rule-1');
    await client.deleteWatchlist('wl-1');
    const calls = vi.mocked(fetch).mock.calls;
    expect(calls.map(([url, init]) => `${init?.method ?? 'GET'} ${url}`)).toEqual([
      'GET /api/v1/watchlists',
      'GET /api/v1/watchlists/wl-1',
      'PUT /api/v1/watchlists/wl-1',
      'DELETE /api/v1/triggers?acknowledged_only=true',
      'DELETE /api/v1/alert-rules/rule-1',
      'DELETE /api/v1/watchlists/wl-1',
    ]);
    expect(JSON.parse(String(calls[2][1]?.body))).toEqual({ name: 'New name', symbols: ['ETHUSDT'] });
  });
});
