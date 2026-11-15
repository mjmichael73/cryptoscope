import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

const links = [
  { to: '/', label: 'Dashboard', icon: '◉' },
  { to: '/market-data', label: 'Market Data', icon: '▤' },
  { to: '/watchlists', label: 'Watchlists', icon: '☰' },
  { to: '/alert-rules', label: 'Alert Rules', icon: '⚑' },
  { to: '/triggers', label: 'Triggers', icon: '⚡' },
  { to: '/health', label: 'System', icon: '◎' },
];

function SidebarContents({ onNavigate, onClose }: { onNavigate?: () => void; onClose?: () => void }) {
  const { user, logout } = useAuth();
  return <>
    <div className="flex items-center justify-between border-b border-gray-800 px-5 py-4">
      <div>
        <h1 className="text-lg font-bold tracking-tight text-violet-300">cryptoscope</h1>
        <p className="mt-0.5 text-xs text-gray-400">market analytics</p>
      </div>
      {onClose && <button type="button" aria-label="Close navigation" aria-expanded="true" onClick={onClose} className="grid min-h-11 min-w-11 place-items-center rounded-lg text-gray-300 hover:bg-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400">×</button>}
    </div>
    <nav aria-label={onClose ? 'Mobile navigation' : 'Primary navigation'} className="flex-1 py-3">
      {links.map((link) => <NavLink
        key={link.to}
        to={link.to}
        end={link.to === '/'}
        onClick={onNavigate}
        className={({ isActive }) => `flex min-h-11 items-center gap-3 border-r-2 px-5 text-sm transition-colors ${isActive ? 'border-violet-400 bg-violet-600/15 text-violet-200' : 'border-transparent text-gray-300 hover:bg-gray-800/70 hover:text-white'}`}
      >
        <span aria-hidden="true" className="w-4 text-center text-xs">{link.icon}</span>
        {link.label}
      </NavLink>)}
    </nav>
    <div className="border-t border-gray-800 px-4 py-4">
      <p className="truncate px-1 text-sm font-medium text-gray-200">{user.username ?? 'Account'}</p>
      <p className="px-1 pt-0.5 text-xs text-gray-400">Signed in</p>
      <button type="button" onClick={logout} className="mt-3 min-h-11 w-full rounded-lg border border-gray-700 px-3 text-left text-sm text-gray-200 transition-colors hover:bg-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400">Logout</button>
      <p className="px-1 pt-3 text-xs text-gray-500">v0.1.0</p>
    </div>
  </>;
}

export default function Layout() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  return (
    <div className="flex min-h-screen bg-gray-950">
      <aside className="hidden w-60 shrink-0 flex-col border-r border-gray-800 bg-gray-900 lg:flex">
        <SidebarContents />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-14 items-center gap-3 border-b border-gray-800 bg-gray-900 px-4 lg:hidden">
          <button type="button" aria-label="Open navigation" aria-expanded={drawerOpen} aria-controls="mobile-navigation" onClick={() => setDrawerOpen(true)} className="grid min-h-11 min-w-11 place-items-center rounded-lg text-gray-200 hover:bg-gray-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-violet-400">
            <span aria-hidden="true" className="text-xl">☰</span>
          </button>
          <span className="font-semibold tracking-tight text-violet-300">cryptoscope</span>
        </header>
        {drawerOpen && <div className="fixed inset-0 z-50 lg:hidden">
          <button type="button" aria-label="Dismiss navigation backdrop" onClick={() => setDrawerOpen(false)} className="absolute inset-0 h-full w-full bg-black/60" />
          <aside id="mobile-navigation" role="dialog" aria-modal="true" aria-label="Mobile navigation" className="relative flex h-full w-[min(19rem,85vw)] flex-col border-r border-gray-700 bg-gray-900 shadow-2xl">
            <SidebarContents onNavigate={() => setDrawerOpen(false)} onClose={() => setDrawerOpen(false)} />
          </aside>
        </div>}
        <main className="min-w-0 flex-1 overflow-y-auto p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
