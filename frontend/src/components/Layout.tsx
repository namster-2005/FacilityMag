import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'

const nav = [
  { to: '/dashboard',   label: 'Dashboard',    icon: '📊' },
  { to: '/assets',      label: 'Assets',        icon: '🪑' },
  { to: '/tickets',     label: 'Tickets',       icon: '🎫' },
  { to: '/maintenance', label: 'Maintenance',   icon: '🔧' },
]

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    navigate('/login')
  }

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-slate-900 flex flex-col shrink-0">
        <div className="px-5 py-5 border-b border-slate-700">
          <div className="text-white font-bold text-lg">AssetBase</div>
          <div className="text-slate-400 text-xs mt-0.5">Facility Management</div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {nav.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  isActive
                    ? 'bg-emerald-600 text-white'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <span>{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="px-4 py-4 border-t border-slate-700">
          <div className="text-slate-300 text-sm font-medium truncate">{user?.name}</div>
          <div className="text-slate-500 text-xs capitalize">{user?.role}</div>
          <button
            onClick={handleLogout}
            className="mt-2 text-xs text-slate-400 hover:text-white transition"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  )
}
