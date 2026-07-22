import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Dashboard", icon: "◉" },
  { to: "/market-data", label: "Market Data", icon: "▤" },
  { to: "/watchlists", label: "Watchlists", icon: "☰" },
  { to: "/alert-rules", label: "Alert Rules", icon: "⚑" },
  { to: "/triggers", label: "Triggers", icon: "⚡" },
  { to: "/health", label: "System", icon: "◎" },
];

export default function Layout() {
  return (
    <div className="flex h-screen">
      <aside className="w-56 shrink-0 border-r border-gray-800 bg-gray-900 flex flex-col">
        <div className="px-5 py-4 border-b border-gray-800">
          <h1 className="text-lg font-bold tracking-tight text-violet-400">
            cryptoscope
          </h1>
          <p className="text-[11px] text-gray-500 mt-0.5">market analytics</p>
        </div>
        <nav className="flex-1 py-3">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              end={l.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-violet-600/15 text-violet-300 border-r-2 border-violet-400"
                    : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/50"
                }`
              }
            >
              <span className="w-4 text-center text-xs">{l.icon}</span>
              {l.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-3 border-t border-gray-800 text-[11px] text-gray-600">
          v0.1.0
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
