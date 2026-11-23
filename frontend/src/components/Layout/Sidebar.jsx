import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Map,
  AlertTriangle,
  BarChart3,
  Settings,
  Anchor,
  Shield,
  Radio,
} from 'lucide-react'

const navItems = [
  { to: '/dashboard',       icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/vessel-tracking', icon: Map,             label: 'Vessel Tracking' },
  { to: '/anomaly-alerts',  icon: AlertTriangle,   label: 'Anomaly Alerts' },
  { to: '/analytics',       icon: BarChart3,       label: 'Analytics' },
  { to: '/settings',        icon: Settings,        label: 'Settings' },
]

export default function Sidebar() {
  return (
    <aside className="w-64 flex-shrink-0 bg-navy-800/80 backdrop-blur-sm border-r border-navy-600/30 flex flex-col">
      {/* Logo / Brand */}
      <div className="px-5 py-5 border-b border-navy-600/30">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-ocean-600/20 border border-ocean-600/40 flex items-center justify-center">
            <Shield className="w-5 h-5 text-ocean-400" />
          </div>
          <div>
            <h1 className="text-white font-semibold text-sm leading-none">MaritimeGuard</h1>
            <p className="text-ocean-500 text-xs mt-0.5">AI Anomaly Detection</p>
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="px-4 py-3 mx-4 mt-4 rounded-lg bg-alert-green/10 border border-alert-green/20">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-alert-green opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-alert-green"></span>
          </span>
          <span className="text-xs text-alert-green font-medium">System Online</span>
        </div>
        <div className="flex items-center gap-2 mt-1.5">
          <Radio className="w-3 h-3 text-slate-400" />
          <span className="text-xs text-slate-400">AIS Feed Active</span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="label-text px-3 mb-3">Navigation</p>
        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            id={`nav-${label.toLowerCase().replace(/\s+/g, '-')}`}
            className={({ isActive }) =>
              isActive ? 'nav-item-active' : 'nav-item'
            }
          >
            <Icon className="w-4 h-4 flex-shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-navy-600/30">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-ocean-700/40 border border-ocean-600/30 flex items-center justify-center">
            <Anchor className="w-4 h-4 text-ocean-400" />
          </div>
          <div>
            <p className="text-xs text-white font-medium">Admin User</p>
            <p className="text-xs text-slate-500">Maritime Control</p>
          </div>
        </div>
      </div>
    </aside>
  )
}
