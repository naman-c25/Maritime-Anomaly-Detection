import { Link } from 'react-router-dom'
import {
  Ship, AlertTriangle, MapPin, Cpu,
  TrendingUp, TrendingDown, ArrowUpRight,
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend,
} from 'recharts'
import { kpiData, recentAlerts, anomalyTrend, vesselsByType } from '../data/mockData'
import { getSeverityBadge, getStatusBadge } from '../utils/helpers'

const iconMap = { Ship, AlertTriangle, MapPin, Cpu }

const colorMap = {
  ocean: { bg: 'bg-ocean-700/20', border: 'border-ocean-600/30', icon: 'text-ocean-400', ring: '#00b4d8' },
  red:   { bg: 'bg-red-500/10',   border: 'border-red-500/20',   icon: 'text-red-400',   ring: '#ef4444' },
  green: { bg: 'bg-green-500/10', border: 'border-green-500/20', icon: 'text-green-400', ring: '#10b981' },
  amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', icon: 'text-amber-400', ring: '#f59e0b' },
}

function KpiCard({ id, label, value, delta, deltaUp, icon, color }) {
  const Icon = iconMap[icon]
  const c = colorMap[color]
  return (
    <div id={id} className="glass-card-hover p-5 flex flex-col gap-4 animate-fade-in">
      <div className="flex items-start justify-between">
        <div className={`w-10 h-10 rounded-lg ${c.bg} border ${c.border} flex items-center justify-center`}>
          <Icon className={`w-5 h-5 ${c.icon}`} />
        </div>
        <span className={`flex items-center gap-1 text-xs font-medium ${deltaUp ? 'text-green-400' : 'text-red-400'}`}>
          {deltaUp ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
          {delta}
        </span>
      </div>
      <div>
        <p className="label-text mb-1">{label}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="glass-card p-3 text-xs space-y-1 shadow-ocean">
      <p className="text-slate-400 font-medium mb-2">{label}</p>
      {payload.map(p => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: p.color }} />
          <span className="text-slate-300 capitalize">{p.name}:</span>
          <span className="text-white font-medium">{p.value}</span>
        </div>
      ))}
    </div>
  )
}

export default function Dashboard() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Maritime Surveillance</h2>
          <p className="text-slate-400 text-sm mt-0.5">Real-time AI-powered anomaly monitoring</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Live · Auto-updating every 30s
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {kpiData.map(kpi => <KpiCard key={kpi.id} {...kpi} />)}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Area Chart */}
        <div className="lg:col-span-2 glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="section-title">Anomaly Trend (Today)</h3>
            <span className="label-text">Hourly breakdown</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={anomalyTrend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="gradSpoofing"  x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradDark"      x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#00b4d8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00b4d8" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradSpeed"     x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%"  stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a3a5c40" />
              <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="spoofing"    stroke="#ef4444" fill="url(#gradSpoofing)" strokeWidth={2} />
              <Area type="monotone" dataKey="darkShip"    stroke="#00b4d8" fill="url(#gradDark)"     strokeWidth={2} />
              <Area type="monotone" dataKey="speedAnomaly" stroke="#f59e0b" fill="url(#gradSpeed)"   strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
          <div className="flex gap-4 mt-3">
            {[['AIS Spoofing','#ef4444'],['Dark Ship','#00b4d8'],['Speed Anomaly','#f59e0b']].map(([name, color]) => (
              <div key={name} className="flex items-center gap-1.5">
                <span className="w-2.5 h-0.5 rounded-full" style={{ background: color }} />
                <span className="text-xs text-slate-400">{name}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Pie Chart */}
        <div className="glass-card p-5">
          <h3 className="section-title mb-4">Vessels by Type</h3>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={vesselsByType} cx="50%" cy="50%" innerRadius={50} outerRadius={80}
                   paddingAngle={3} dataKey="value">
                {vesselsByType.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(v, n) => [v, n]} contentStyle={{ background: '#0d1b2a', border: '1px solid #1a3a5c', borderRadius: '8px', fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
          <div className="space-y-2 mt-2">
            {vesselsByType.map(v => (
              <div key={v.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: v.color }} />
                  <span className="text-slate-400">{v.name}</span>
                </div>
                <span className="text-white font-medium">{v.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Alerts Table */}
      <div className="glass-card">
        <div className="flex items-center justify-between px-5 py-4 border-b border-navy-600/30">
          <h3 className="section-title">Recent Anomaly Alerts</h3>
          <Link to="/anomaly-alerts" className="flex items-center gap-1 text-xs text-ocean-400 hover:text-ocean-300 transition-colors">
            View all <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" id="recent-alerts-table">
            <thead>
              <tr className="border-b border-navy-600/20">
                {['Alert ID','Vessel','Type','Severity','Zone','Time','Status'].map(h => (
                  <th key={h} className="label-text px-5 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-600/15">
              {recentAlerts.map(a => (
                <tr key={a.id} className="table-row-hover">
                  <td className="px-5 py-3 font-mono text-ocean-400 text-xs">{a.id}</td>
                  <td className="px-5 py-3">
                    <p className="text-white font-medium">{a.vessel}</p>
                    <p className="text-slate-500 text-xs">{a.mmsi}</p>
                  </td>
                  <td className="px-5 py-3 text-slate-300">{a.type}</td>
                  <td className="px-5 py-3">
                    <span className={getSeverityBadge(a.severity)}>{a.severity}</span>
                  </td>
                  <td className="px-5 py-3 text-slate-400">{a.zone}</td>
                  <td className="px-5 py-3 text-slate-400 font-mono text-xs">{a.time}</td>
                  <td className="px-5 py-3">
                    <span className={getStatusBadge(a.status)}>{a.status}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
