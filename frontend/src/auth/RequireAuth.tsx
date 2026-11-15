import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

export default function RequireAuth() {
  const { status } = useAuth();
  const location = useLocation();
  if (status === 'loading') {
    return <main className="grid min-h-screen place-items-center bg-slate-950 text-slate-300" aria-label="Loading session">Loading session…</main>;
  }
  if (status === 'unauthenticated') {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return <Outlet />;
}
