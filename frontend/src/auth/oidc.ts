export type OidcConfig = {
  issuer: string;
  clientId: string;
};

export type TokenResponse = {
  access_token: string;
  refresh_token?: string;
  expires_in: number;
  id_token?: string;
};

type JwtPayload = {
  sub?: string;
  preferred_username?: string;
  exp?: number;
  tenant_id?: string;
};

const tokenEndpoint = (config: OidcConfig) =>
  `${config.issuer.replace(/\/+$/, '')}/protocol/openid-connect/token`;

const encodeBase64Url = (bytes: Uint8Array): string => {
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
};

export function oidcConfigFromEnv(): OidcConfig {
  return {
    issuer: import.meta.env.VITE_OIDC_ISSUER || '/auth/realms/cryptoscope',
    clientId: import.meta.env.VITE_OIDC_CLIENT_ID || 'cryptoscope-frontend',
  };
}

export async function createPkcePair(): Promise<{ verifier: string; challenge: string }> {
  const random = new Uint8Array(32);
  globalThis.crypto.getRandomValues(random);
  const verifier = encodeBase64Url(random);
  const digest = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  return { verifier, challenge: encodeBase64Url(new Uint8Array(digest)) };
}

export function buildAuthorizeUrl(
  config: OidcConfig,
  challenge: string,
  state: string,
  redirectUri: string,
): string {
  const url = new URL(`${config.issuer.replace(/\/+$/, '')}/protocol/openid-connect/auth`, window.location.origin);
  url.search = new URLSearchParams({
    client_id: config.clientId,
    response_type: 'code',
    scope: 'openid profile email',
    redirect_uri: redirectUri,
    state,
    code_challenge: challenge,
    code_challenge_method: 'S256',
  }).toString();
  return url.toString();
}

export async function exchangeCode(
  config: OidcConfig,
  code: string,
  verifier: string,
  redirectUri: string,
): Promise<TokenResponse> {
  const body = new URLSearchParams({
    grant_type: 'authorization_code',
    client_id: config.clientId,
    code,
    code_verifier: verifier,
    redirect_uri: redirectUri,
  });
  return tokenRequestAt(config, body);
}

export async function refreshToken(config: OidcConfig, refresh: string): Promise<TokenResponse> {
  return tokenRequestAt(config, new URLSearchParams({
    grant_type: 'refresh_token',
    client_id: config.clientId,
    refresh_token: refresh,
  }));
}

async function tokenRequestAt(config: OidcConfig, body: URLSearchParams): Promise<TokenResponse> {
  const response = await fetch(tokenEndpoint(config), {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  });
  if (!response.ok) throw new Error(`Token request failed: HTTP ${response.status}`);
  return (await response.json()) as TokenResponse;
}

export function decodeJwt(token: string): JwtPayload {
  const payload = token.split('.')[1];
  if (!payload) throw new Error('Invalid JWT');
  const base64 = payload.replace(/-/g, '+').replace(/_/g, '/');
  const padded = base64.padEnd(Math.ceil(base64.length / 4) * 4, '=');
  return JSON.parse(new TextDecoder().decode(Uint8Array.from(atob(padded), (char) => char.charCodeAt(0)))) as JwtPayload;
}
