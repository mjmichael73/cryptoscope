import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { exchangeCode, oidcConfigFromEnv } from '../auth/oidc';

const oauthStateKey = 'cryptoscope.auth.oauth_state';
const verifierKey = 'cryptoscope.auth.pkce_verifier';
const returnToKey = 'cryptoscope.auth.return_to';

export default function Callback() {
  const location = useLocation();
  const navigate = useNavigate();
  const { completeLogin } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get('code');
    const state = params.get('state');
    const expectedState = sessionStorage.getItem(oauthStateKey);
    const verifier = sessionStorage.getItem(verifierKey);
    if (!code || !state || state !== expectedState || !verifier) {
      setError('Could not verify sign-in request. Please try signing in again.');
      return;
    }

    const finish = async () => {
      try {
        const tokens = await exchangeCode(
          oidcConfigFromEnv(),
          code,
          verifier,
          `${window.location.origin}/callback`,
        );
        completeLogin(tokens);
        const destination = sessionStorage.getItem(returnToKey) || '/';
        sessionStorage.removeItem(oauthStateKey);
        sessionStorage.removeItem(verifierKey);
        sessionStorage.removeItem(returnToKey);
        navigate(destination, { replace: true });
      } catch {
        setError('Sign-in could not be completed. Please try again.');
      }
    };
    void finish();
  }, [completeLogin, location.search, navigate]);

  return <main className="grid min-h-screen place-items-center bg-slate-950 px-5 text-slate-100">
    <section className="w-full max-w-md rounded-2xl border border-white/10 bg-slate-900 p-8 text-center">
      {error ? <>
        <h1 className="text-xl font-semibold">Sign-in failed</h1>
        <p role="alert" className="mt-3 text-sm leading-6 text-rose-300">{error}</p>
        <a href="/login" className="mt-6 inline-flex min-h-11 items-center rounded-lg bg-violet-500 px-4 text-sm font-semibold text-white">Return to sign in</a>
      </> : <>
        <h1 className="text-xl font-semibold">Finishing sign-in</h1>
        <p className="mt-3 text-sm text-slate-400" aria-live="polite">Connecting your workspace…</p>
      </>}
    </section>
  </main>;
}
