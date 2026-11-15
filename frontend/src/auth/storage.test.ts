import { beforeEach, describe, expect, it } from 'vitest';
import { clearSession, loadSession, saveSession, updateAccessToken, type AuthSession } from './storage';

const session: AuthSession = {
  accessToken: 'access',
  refreshToken: 'refresh',
  expiresAt: 1234,
  idToken: 'id-token',
  username: 'mira',
};

beforeEach(() => sessionStorage.clear());

describe('auth session storage', () => {
  it('round-trips a session in sessionStorage', () => {
    saveSession(session);
    expect(loadSession()).toEqual(session);
    expect(sessionStorage.length).toBeGreaterThan(0);
  });

  it('clears the stored session', () => {
    saveSession(session);
    clearSession();
    expect(loadSession()).toBeNull();
  });

  it('updates just the access token and expiry', () => {
    saveSession(session);
    updateAccessToken('new-access', 5678);
    expect(loadSession()).toEqual({ ...session, accessToken: 'new-access', expiresAt: 5678 });
  });
});
