import { createHash } from 'node:crypto';
import { afterEach, describe, expect, it, vi } from 'vitest';
import {
  buildAuthorizeUrl,
  createPkcePair,
  decodeJwt,
  exchangeCode,
  refreshToken,
  type OidcConfig,
} from './oidc';

const config: OidcConfig = { issuer: 'https://issuer.example/realms/demo/', clientId: 'frontend' };
const base64url = (value: string) => Buffer.from(value).toString('base64url');

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('OIDC helpers', () => {
  it('creates an RFC 7636 S256 PKCE pair', async () => {
    const pair = await createPkcePair();
    expect(pair.verifier.length).toBeGreaterThanOrEqual(43);
    const expected = createHash('sha256').update(pair.verifier).digest('base64url');
    expect(pair.challenge).toBe(expected);
  });

  it('builds the authorize URL with PKCE and redirect state', () => {
    const url = new URL(buildAuthorizeUrl(config, 'challenge-value', 'state-value', 'http://localhost/callback'));
    expect(url.origin + url.pathname).toBe('https://issuer.example/realms/demo/protocol/openid-connect/auth');
    expect(url.searchParams.get('client_id')).toBe('frontend');
    expect(url.searchParams.get('response_type')).toBe('code');
    expect(url.searchParams.get('scope')).toBe('openid profile email');
    expect(url.searchParams.get('redirect_uri')).toBe('http://localhost/callback');
    expect(url.searchParams.get('state')).toBe('state-value');
    expect(url.searchParams.get('code_challenge')).toBe('challenge-value');
    expect(url.searchParams.get('code_challenge_method')).toBe('S256');
  });

  it('exchanges an authorization code with a form encoded POST', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ access_token: 'a', expires_in: 60 }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    await expect(exchangeCode(config, 'auth-code', 'pkce-verifier', 'http://localhost/callback')).resolves.toMatchObject({ access_token: 'a', expires_in: 60 });
    expect(fetchMock).toHaveBeenCalledWith('https://issuer.example/realms/demo/protocol/openid-connect/token', expect.objectContaining({
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: expect.any(URLSearchParams),
    }));
    const body = fetchMock.mock.calls[0][1].body as URLSearchParams;
    expect(body.get('grant_type')).toBe('authorization_code');
    expect(body.get('code')).toBe('auth-code');
    expect(body.get('code_verifier')).toBe('pkce-verifier');
  });

  it('refreshes a token using the refresh-token grant', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ access_token: 'fresh', expires_in: 120 }), { status: 200 }));
    vi.stubGlobal('fetch', fetchMock);
    await expect(refreshToken(config, 'refresh-me')).resolves.toMatchObject({ access_token: 'fresh' });
    const body = fetchMock.mock.calls[0][1].body as URLSearchParams;
    expect(body.get('grant_type')).toBe('refresh_token');
    expect(body.get('refresh_token')).toBe('refresh-me');
  });

  it('decodes the JWT payload without treating it as verified', () => {
    const token = `header.${base64url(JSON.stringify({ sub: '123', preferred_username: 'mira', exp: 1, tenant_id: 'tenant-a' }))}.signature`;
    expect(decodeJwt(token)).toEqual({ sub: '123', preferred_username: 'mira', exp: 1, tenant_id: 'tenant-a' });
  });
});
