import { useLocation } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function Login() {
  const { login, loginDemo } = useAuth();
  const location = useLocation();
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname;
  const showDemo = import.meta.env.VITE_DEV_AUTH === '1';

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-5 py-12 text-slate-100">
      <section className="grid w-full max-w-5xl overflow-hidden rounded-3xl border border-white/10 bg-slate-900/70 shadow-2xl shadow-black/30 md:grid-cols-[1.1fr_0.9fr]">
        <div className="flex flex-col justify-between bg-gradient-to-br from-violet-950 via-slate-900 to-slate-900 p-8 sm:p-12">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.22em] text-violet-300">Cryptoscope</p>
            <h1 className="mt-12 max-w-md text-4xl font-semibold leading-tight tracking-tight sm:text-5xl">A clearer view of the crypto markets.</h1>
            <p className="mt-5 max-w-md text-base leading-7 text-slate-300">Follow price movements, build watchlists, and keep your alert history in one place.</p>
          </div>
          <p className="mt-16 text-sm text-slate-400">Market data and alerts for your workspace.</p>
        </div>
        <div className="flex flex-col justify-center p-8 sm:p-12">
          <h2 className="text-2xl font-semibold">Sign in to continue</h2>
          <p className="mt-2 text-sm leading-6 text-slate-400">Use your organization account to access your market workspace.</p>
          <button type="button" onClick={() => void login(from)} className="mt-8 min-h-12 rounded-xl bg-violet-500 px-5 py-3 text-sm font-semibold text-white transition-colors hover:bg-violet-400 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-300">
            Sign in with Keycloak
          </button>
          {showDemo && <>
            <div className="my-6 flex items-center gap-3 text-xs uppercase tracking-wider text-slate-500"><span className="h-px flex-1 bg-slate-700" />Development access<span className="h-px flex-1 bg-slate-700" /></div>
            <button type="button" onClick={loginDemo} className="min-h-12 rounded-xl border border-slate-600 px-5 py-3 text-sm font-semibold text-slate-200 transition-colors hover:border-slate-400 hover:bg-white/5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-violet-300">
              Demo login
            </button>
          </>}
        </div>
      </section>
    </main>
  );
}
