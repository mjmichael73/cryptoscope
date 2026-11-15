export type AuthSession = {
  accessToken: string;
  refreshToken: string | null;
  expiresAt: number;
  idToken: string | null;
  username: string | null;
};

const keys = {
  accessToken: 'cryptoscope.auth.access_token',
  refreshToken: 'cryptoscope.auth.refresh_token',
  expiresAt: 'cryptoscope.auth.expires_at',
  idToken: 'cryptoscope.auth.id_token',
  username: 'cryptoscope.auth.username',
} as const;

export function loadSession(): AuthSession | null {
  const accessToken = sessionStorage.getItem(keys.accessToken);
  const expiresAt = Number(sessionStorage.getItem(keys.expiresAt));
  if (!accessToken || !Number.isFinite(expiresAt) || expiresAt <= 0) return null;
  return {
    accessToken,
    refreshToken: sessionStorage.getItem(keys.refreshToken),
    expiresAt,
    idToken: sessionStorage.getItem(keys.idToken),
    username: sessionStorage.getItem(keys.username),
  };
}

export function saveSession(session: AuthSession): void {
  sessionStorage.setItem(keys.accessToken, session.accessToken);
  sessionStorage.setItem(keys.expiresAt, String(session.expiresAt));
  session.refreshToken === null
    ? sessionStorage.removeItem(keys.refreshToken)
    : sessionStorage.setItem(keys.refreshToken, session.refreshToken);
  session.idToken === null
    ? sessionStorage.removeItem(keys.idToken)
    : sessionStorage.setItem(keys.idToken, session.idToken);
  session.username === null
    ? sessionStorage.removeItem(keys.username)
    : sessionStorage.setItem(keys.username, session.username);
}

export function clearSession(): void {
  Object.values(keys).forEach((key) => sessionStorage.removeItem(key));
}

export function updateAccessToken(accessToken: string, expiresAt: number): void {
  const session = loadSession();
  if (session) saveSession({ ...session, accessToken, expiresAt });
}
