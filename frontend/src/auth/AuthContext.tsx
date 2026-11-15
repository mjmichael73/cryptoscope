import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  buildAuthorizeUrl,
  createPkcePair,
  decodeJwt,
  oidcConfigFromEnv,
  refreshToken,
  type TokenResponse,
} from './oidc';
import { clearSession, loadSession, saveSession, type AuthSession } from './storage';

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated';
export type AuthUser = { username: string | null };
export type AuthContextValue = {
  user: AuthUser;
  token: string | null;
  status: AuthStatus;
  login(from?: string): void;
  loginDemo(): void;
  logout(): void;
  completeLogin(tokens: TokenResponse): void;
};

const AuthContext = createContext<AuthContextValue | null>(null);
const oauthStateKey = 'cryptoscope.auth.oauth_state';
const verifierKey = 'cryptoscope.auth.pkce_verifier';
const returnToKey = 'cryptoscope.auth.return_to';

function usernameFromToken(token: string, fallback: string | null): string | null {
  try {
    return decodeJwt(token).preferred_username ?? fallback;
  } catch {
    return fallback;
  }
}

function sessionFromTokens(tokens: TokenResponse, previous?: AuthSession | null): AuthSession {
  return {
    accessToken: tokens.access_token,
    refreshToken: tokens.refresh_token ?? previous?.refreshToken ?? null,
    expiresAt: Date.now() + tokens.expires_in * 1000,
    idToken: tokens.id_token ?? previous?.idToken ?? null,
    username: usernameFromToken(tokens.access_token, previous?.username ?? null),
  };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');

  const logout = useCallback(() => {
    const idToken = loadSession()?.idToken;
    clearSession();
    setSession(null);
    setStatus('unauthenticated');
    if (idToken) {
      const config = oidcConfigFromEnv();
      const url = new URL(`${config.issuer.replace(/\/+$/, '')}/protocol/openid-connect/logout`, window.location.origin);
      url.searchParams.set('id_token_hint', idToken);
      url.searchParams.set('post_logout_redirect_uri', window.location.origin);
      window.location.assign(url.toString());
    }
  }, []);

  const completeLogin = useCallback((tokens: TokenResponse) => {
    const next = sessionFromTokens(tokens);
    saveSession(next);
    setSession(next);
    setStatus('authenticated');
  }, []);

  const refreshSession = useCallback(async (current: AuthSession) => {
    if (!current.refreshToken) {
      logout();
      return;
    }
    try {
      const tokens = await refreshToken(oidcConfigFromEnv(), current.refreshToken);
      const next = sessionFromTokens(tokens, current);
      saveSession(next);
      setSession(next);
      setStatus('authenticated');
    } catch {
      logout();
    }
  }, [logout]);

  useEffect(() => {
    let cancelled = false;
    const restore = async () => {
      const stored = loadSession();
      if (!stored) {
        if (!cancelled) setStatus('unauthenticated');
        return;
      }
      if (stored.expiresAt <= Date.now()) {
        if (stored.refreshToken) await refreshSession(stored);
        else logout();
        return;
      }
      if (!cancelled) {
        setSession(stored);
        setStatus('authenticated');
      }
    };
    void restore();
    return () => {
      cancelled = true;
    };
  }, [logout, refreshSession]);

  useEffect(() => {
    if (status !== 'authenticated' || !session?.refreshToken) return;
    const delay = Math.max(0, session.expiresAt - Date.now() - 60_000);
    const timer = setTimeout(() => void refreshSession(session), delay);
    return () => clearTimeout(timer);
  }, [refreshSession, session, status]);

  const login = useCallback(async (from?: string) => {
    const config = oidcConfigFromEnv();
    const pair = await createPkcePair();
    const stateBytes = new Uint8Array(24);
    crypto.getRandomValues(stateBytes);
    const state = Array.from(stateBytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
    sessionStorage.setItem(oauthStateKey, state);
    sessionStorage.setItem(verifierKey, pair.verifier);
    if (from && from !== '/login' && from !== '/callback') sessionStorage.setItem(returnToKey, from);
    const redirectUri = `${window.location.origin}/callback`;
    window.location.assign(buildAuthorizeUrl(config, pair.challenge, state, redirectUri));
  }, []);

  const loginDemo = useCallback(() => {
    const demo: AuthSession = {
      accessToken: 'demo-local-session',
      refreshToken: null,
      expiresAt: Date.now() + 8 * 60 * 60 * 1000,
      idToken: null,
      username: 'demo',
    };
    saveSession(demo);
    setSession(demo);
    setStatus('authenticated');
  }, []);

  const value = useMemo<AuthContextValue>(() => ({
    user: { username: session?.username ?? null },
    token: session?.accessToken ?? null,
    status,
    login,
    loginDemo,
    logout,
    completeLogin,
  }), [session, status, login, loginDemo, logout, completeLogin]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used within AuthProvider');
  return value;
}
