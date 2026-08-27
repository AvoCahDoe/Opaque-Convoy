import { NavLink, Outlet } from 'react-router-dom'

const links = [
  { to: '/doc', label: 'Doc' },
  { to: '/try', label: 'Try' },
  { to: '/results', label: 'Results' },
]

export default function Layout() {
  return (
    <div className="app-shell h-full min-h-0 flex flex-col">
      <header className="oc-nav shrink-0 z-30 flex items-center justify-between gap-4 px-4 md:px-6 py-3 border-b border-[rgba(26,31,38,0.12)] bg-[rgba(248,249,250,0.92)] backdrop-blur-md">
        <NavLink to="/try" className="font-display text-xl md:text-2xl text-[var(--ink-strong)] no-underline tracking-tight">
          Opaque Convoy
        </NavLink>
        <nav className="flex items-center gap-1 md:gap-2">
          {links.map((l) => (
            <NavLink
              key={l.to}
              to={l.to}
              className={({ isActive }) =>
                `oc-nav-link ${isActive ? 'oc-nav-link-active' : ''}`
              }
            >
              {l.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1 min-h-0 relative">
        <Outlet />
      </main>
    </div>
  )
}
