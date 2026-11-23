import { useState, useEffect, useRef } from 'react'
import { Bell, Search, ChevronRight, Home, X, AlertTriangle } from 'lucide-react'
import { useLocation, Link } from 'react-router-dom'
import { useLiveData } from '../../data/liveData'
import { getSeverityBadge } from '../../utils/helpers'

const pageNames = {
  '/dashboard':        'Dashboard',
  '/live-analysis':    'Live Analysis',
  '/vessel-tracking':  'Vessel Tracking',
  '/anomaly-alerts':   'Anomaly Alerts',
  '/analytics':        'Analytics',
  '/settings':         'Settings',
}

export default function TopNav() {
  const { pathname } = useLocation()
  const currentPage = pageNames[pathname] ?? 'Dashboard'
  const { allAlerts } = useLiveData()
  const activeAlerts = allAlerts.filter(a => a.status === 'Active').slice(0, 3)

  // Live UTC clock — updates every second
  const [now, setNow] = useState(new Date())
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  // Notification panel toggle with click-outside close
  const [showNotif, setShowNotif] = useState(false)
  const notifRef = useRef(null)
  useEffect(() => {
    function handleClickOutside(e) {
      if (notifRef.current && !notifRef.current.contains(e.target)) {
        setShowNotif(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  return (
    <header className="h-16 bg-navy-800/60 backdrop-blur-sm border-b border-navy-600/30 flex items-center px-6 gap-4 flex-shrink-0 relative z-40">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm flex-1">
        <Home className="w-3.5 h-3.5 text-slate-500" />
        <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
        <span className="text-ocean-400 font-medium">{currentPage}</span>
      </div>

      {/* Search — UI element; global search to be wired in a future phase */}
      <div className="relative hidden md:flex items-center">
        <Search className="absolute left-3 w-4 h-4 text-slate-500" />
        <input
          id="topnav-search"
          type="text"
          placeholder="Search vessels, alerts..."
          className="bg-navy-700/50 border border-navy-600/40 text-sm text-slate-300 placeholder-slate-600
                     rounded-lg pl-9 pr-4 py-2 w-64 focus:outline-none focus:border-ocean-600/60
                     focus:ring-1 focus:ring-ocean-600/30 transition-all"
        />
      </div>

      {/* Notifications */}
      <div className="relative" ref={notifRef}>
        <button
          id="topnav-notifications"
          onClick={() => setShowNotif(prev => !prev)}
          className="relative p-2 rounded-lg hover:bg-navy-700/60 text-slate-400 hover:text-white transition-colors"
          aria-label="Toggle notifications"
        >
          <Bell className="w-5 h-5" />
          {activeAlerts.length > 0 && (
            <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-alert-red rounded-full">
              <span className="absolute inset-0 rounded-full bg-alert-red animate-ping opacity-75" />
            </span>
          )}
        </button>

        {/* Notification dropdown */}
        {showNotif && (
          <div
            id="notifications-panel"
            className="absolute right-0 top-full mt-2 w-80 glass-card shadow-ocean-lg animate-fade-in"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-navy-600/30">
              <h3 className="text-sm font-semibold text-white">
                Active Alerts
              </h3>
              <button
                onClick={() => setShowNotif(false)}
                className="text-slate-500 hover:text-white transition-colors p-0.5"
                aria-label="Close notifications"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="divide-y divide-navy-600/15">
              {activeAlerts.map(a => (
                <div key={a.id} className="px-4 py-3 hover:bg-navy-700/30 transition-colors">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-400 mt-0.5 flex-shrink-0" />
                    <div className="min-w-0 flex-1">
                      <p className="text-white text-xs font-medium truncate">{a.vessel}</p>
                      <p className="text-slate-400 text-xs">{a.type}</p>
                      <p className="text-slate-500 text-xs mt-0.5">{a.time} · {a.zone}</p>
                    </div>
                    <span className={`${getSeverityBadge(a.severity)} flex-shrink-0 capitalize`}>
                      {a.severity}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="px-4 py-3 border-t border-navy-600/30">
              <Link
                to="/anomaly-alerts"
                onClick={() => setShowNotif(false)}
                className="text-xs text-ocean-400 hover:text-ocean-300 transition-colors"
              >
                View all anomaly alerts →
              </Link>
            </div>
          </div>
        )}
      </div>

      {/* Live UTC timestamp — updates every second */}
      <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-navy-700/40 border border-navy-600/20">
        <span className="w-1.5 h-1.5 rounded-full bg-alert-green animate-pulse" />
        <span className="text-xs text-slate-400 font-mono">
          {now.toUTCString().slice(0, 25)} UTC
        </span>
      </div>
    </header>
  )
}
