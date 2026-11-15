import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AuthProvider, useAuth } from './AuthContext';
import { clearSession, saveSession, type AuthSession } from './storage';

const { mockedRefreshToken, mockedCreatePkcePair, mockedBuildAuthorizeUrl, mockedDecodeJwt } = vi.hoisted(() => ({
  mockedRefreshToken: vi.fn(),
  mockedCreatePkcePair: vi.fn(),
  mockedBuildAuthorizeUrl: vi.fn(),
  mockedDecodeJwt: vi.fn(),
}));

vi.mock('./oidc', () => ({
  oidcConfigFromEnv: () => ({ issuer: '/auth/realms/cryptoscope', clientId: 'client' }),
  refreshToken: mockedRefreshToken,
  createPkcePair: mockedCreatePkcePair,
  buildAuthorizeUrl: mockedBuildAuthorizeUrl,
  decodeJwt: mockedDecodeJwt,
}));

function Probe() {
  const auth = useAuth();
  return <div>
    <span>{auth.status}</span>
    <span>{auth.user.username}</span>
    <span>{auth.token}</span>
    <button onClick={auth.loginDemo}>Demo</button>
    <button onClick={auth.logout}>Logout</button>
  </div>;
}

const validSession: AuthSession = {
  accessToken: 'access', refreshToken: null, expiresAt: Date.now() + 60_000,
  idToken: null, username: 'mira',
};

beforeEach(() => {
  sessionStorage.clear();
  clearSession();
  mockedRefreshToken.mockReset();
  mockedCreatePkcePair.mockReset().mockResolvedValue({ verifier: 'verifier', challenge: 'challenge' });
  mockedBuildAuthorizeUrl.mockReset().mockReturnValue('https://issuer.example/auth');
  mockedDecodeJwt.mockReset().mockReturnValue({ preferred_username: 'mira' });
});

describe('AuthProvider', () => {
  it('restores a valid stored session', async () => {
    saveSession(validSession);
    render(<AuthProvider><Probe /></AuthProvider>);
    expect(await screen.findByText('authenticated')).toBeInTheDocument();
    expect(screen.getByText('mira')).toBeInTheDocument();
    expect(screen.getByText('access')).toBeInTheDocument();
  });

  it('refreshes an expired session and stays authenticated', async () => {
    saveSession({ ...validSession, expiresAt: Date.now() - 1000, refreshToken: 'refresh' });
    mockedRefreshToken.mockResolvedValue({ access_token: 'renewed', refresh_token: 'rotated', expires_in: 3600 });
    render(<AuthProvider><Probe /></AuthProvider>);
    expect(await screen.findByText('renewed')).toBeInTheDocument();
    expect(mockedRefreshToken).toHaveBeenCalledWith(expect.anything(), 'refresh');
    expect(screen.getByText('authenticated')).toBeInTheDocument();
  });

  it('clears a session when refresh fails', async () => {
    saveSession({ ...validSession, expiresAt: Date.now() - 1000, refreshToken: 'dead' });
    mockedRefreshToken.mockRejectedValue(new Error('refresh rejected'));
    render(<AuthProvider><Probe /></AuthProvider>);
    expect(await screen.findByText('unauthenticated')).toBeInTheDocument();
    expect(sessionStorage.getItem('cryptoscope.auth.access_token')).toBeNull();
  });

  it('creates an eight-hour local demo session', async () => {
    render(<AuthProvider><Probe /></AuthProvider>);
    await screen.findByText('unauthenticated');
    const before = Date.now();
    act(() => screen.getByRole('button', { name: 'Demo' }).click());
    expect(await screen.findByText('authenticated')).toBeInTheDocument();
    expect(screen.getByText('demo')).toBeInTheDocument();
    const expiresAt = Number(sessionStorage.getItem('cryptoscope.auth.expires_at'));
    expect(expiresAt).toBeGreaterThanOrEqual(before + 8 * 60 * 60 * 1000);
  });
});
