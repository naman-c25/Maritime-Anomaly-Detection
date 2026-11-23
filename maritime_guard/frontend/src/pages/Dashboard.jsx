import { Link } from 'react-router-dom'
import { Ship, AlertTriangle, Camera, Radio, ArrowUpRight } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine,
  ResponsiveContainer, PieChart, Pie, Cell,
} from 'recharts'
import { useAppData } from '../context/AppData'
import { BackendGate, SourceBanner, TooltipStyle } from '../components/common'
import { getSeverityBadge, getStatusBadge, LEVEL_LABEL, fmt, fmtTime } from '../utils/helpers'

const colorMap = {
  ocean: { bg: 'bg-ocean-700/20', border: 'border-ocean-600/30', icon: 'text-ocean-400' },
  red:   { bg: 'bg-red-500/10',   border: 'border-red-500/20',   icon: 'text-red-400' },
  green: { bg: 'bg-green-500/10', border: 'border-green-500/20', icon: 'text-green-400' },
  amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', icon: 'text-amber-400' },
}
const SERIES_COLORS = ['#ef4444', '#f59e0b', '#a855f7', '#00b4d8', '#10b981']
const TYPE_COLORS = ['#ef4444', '#a855f7', '#f59e0b', '#00b4d8', '#48cae4', '#10b981', '#0077b6']

function KpiCard({ label, value, sub, icon: Icon, color }) {
  const c = colorMap[color]
  return (
    <div className="glass-card-hover p-5 flex flex-col gap-4 animate-fade-in">
      <div className={`w-10 h-10 rounded-lg ${c.bg} border ${c.border} flex items-center justify-center`}>
        <Icon className={`w-5 h-5 ${c.icon}`} />
      </div>
      <div>
        <p className="label-text mb-1">{label}</p>
        <p className="text-2xl font-bold text-white">{value}</p>
        <p className="text-xs text-slate-500 mt-1">{sub}</p>
      </div>
    </div>
  )
}

function DashboardBody() {
  const { state } = useAppData()
  const { ais, vision, alerts } = state
  const vessels = ais?.vessels ?? []
  const tracks = vision?.tracks ?? []
  const active = alerts.filter(a => a.status !== 'Resolved')
  const dark = alerts.filter(a => a.source === 'camera' && !a.mmsi).length
  const tau = ais?.threshold

  // Anomaly-score timelines of the five highest-scoring vessels (log scale: errors span orders of magnitude).
  const top = vessels.filter(v => v.series?.length).slice(0, 5)
  const isTime = ais?.mode === 'raw'

  const byType = Object.entries(alerts.reduce((m, a) => ({ ...m, [a.type]: (m[a.type] || 0) + 1 }), {}))
    .map(([name, value], i) => ({ name, value, color: TYPE_COLORS[i % TYPE_COLORS.length] }))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        <KpiCard label="Vessels on AIS" value={ais?.n_vessels ?? 0} icon={Ship} color="ocean"
                 sub={ais ? `${ais.n_reports.toLocaleString()} reports · ${ais.n_windows.toLocaleString()} windows scored` : 'no AIS data'} />
        <KpiCard label="Open Alerts" value={active.length} icon={AlertTriangle} color="red"
                 sub={`${alerts.filter(a => a.level === 'critical').length} critical · fused AIS + camera`} />
        <KpiCard label="AIS Anomalies" value={ais?.n_anomalous_vessels ?? 0} icon={Radio} color="amber"
                 sub={tau ? `LSTM autoencoder, error > τ = ${fmt(tau, 3)}` : '—'} />
        <KpiCard label="Camera Tracks" value={tracks.length} icon={Camera} color="green"
                 sub={vision ? `${dark} without AIS (dark) · ${vision.duration_s}s video` : 'no video analysed'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 glass-card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="section-title">AIS Anomaly Score Over Time</h3>
            <span className="label-text">Top 5 vessels · log scale</span>
          </div>
          {top.length ? (
            <ResponsiveContainer width="100%" height={240}>
              <LineChart margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3a5c40" />
                <XAxis dataKey="x" type="number" domain={['dataMin', 'dataMax']} allowDuplicatedCategory={false}
                       tickFormatter={v => (isTime ? fmtTime(v).slice(0, 5) : v)}
                       tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis scale="log" domain={['auto', 'auto']} allowDataOverflow
                       tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false}
                       tickFormatter={v => (v >= 1 ? v.toFixed(0) : v.toPrecision(1))} />
                <Tooltip {...TooltipStyle} labelFormatter={v => (isTime ? fmtTime(v) : `row ${v}`)}
                         formatter={(v, n) => [fmt(v, 3), n]} />
                {tau && <ReferenceLine y={tau} stroke="#f59e0b" strokeDasharray="4 4"
                                       label={{ value: 'τ', fill: '#f59e0b', fontSize: 11, position: 'right' }} />}
                {top.map((v, i) => (
                  <Line key={v.mmsi} name={v.name} data={v.series.map(([x, y]) => ({ x, y: Math.max(y, 1e-3) }))}
                        dataKey="y" stroke={SERIES_COLORS[i]} strokeWidth={2} dot={false} isAnimationActive={false} />
                ))}
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="text-sm text-slate-500 py-16 text-center">Load AIS data to see anomaly scores.</p>}
          <div className="flex flex-wrap gap-4 mt-3">
            {top.map((v, i) => (
              <div key={v.mmsi} className="flex items-center gap-1.5">
                <span className="w-2.5 h-0.5 rounded-full" style={{ background: SERIES_COLORS[i] }} />
                <span className="text-xs text-slate-400">{v.name}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="glass-card p-5">
          <h3 className="section-title mb-4">Alerts by Type</h3>
          {byType.length ? (
            <>
              <ResponsiveContainer width="100%" height={170}>
                <PieChart>
                  <Pie data={byType} cx="50%" cy="50%" innerRadius={48} outerRadius={75} paddingAngle={3} dataKey="value"
                       isAnimationActive={false} stroke="none">
                    {byType.map(e => <Cell key={e.name} fill={e.color} />)}
                  </Pie>
                  <Tooltip {...TooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 mt-2">
                {byType.map(t => (
                  <div key={t.name} className="flex items-center justify-between text-xs gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: t.color }} />
                      <span className="text-slate-400 truncate">{t.name}</span>
                    </div>
                    <span className="text-white font-medium">{t.value}</span>
                  </div>
                ))}
              </div>
            </>
          ) : <p className="text-sm text-slate-500 py-16 text-center">No alerts.</p>}
        </div>
      </div>

      <div className="glass-card">
        <div className="flex items-center justify-between px-5 py-4 border-b border-navy-600/30">
          <h3 className="section-title">Latest Fused Alerts</h3>
          <Link to="/anomaly-alerts" className="flex items-center gap-1 text-xs text-ocean-400 hover:text-ocean-300 transition-colors">
            View all <ArrowUpRight className="w-3 h-3" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-navy-600/20">
                {['Alert ID', 'Vessel', 'Type', 'Level', 'Source', 'Fused score', 'Time', 'Status'].map(h => (
                  <th key={h} className="label-text px-5 py-3 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-600/15">
              {alerts.length === 0 && (
                <tr><td colSpan={8} className="text-center py-10 text-slate-500">No alerts.</td></tr>
              )}
              {alerts.slice(0, 6).map(a => (
                <tr key={a.id} className="table-row-hover">
                  <td className="px-5 py-3 font-mono text-ocean-400 text-xs">{a.id}</td>
                  <td className="px-5 py-3">
                    <p className="text-white font-medium">{a.name}</p>
                    <p className="text-slate-500 text-xs">{a.mmsi ? `MMSI ${a.mmsi}` : 'no AIS identity'}</p>
                  </td>
                  <td className="px-5 py-3 text-slate-300">{a.type}</td>
                  <td className="px-5 py-3"><span className={getSeverityBadge(a.level)}>{LEVEL_LABEL[a.level]}</span></td>
                  <td className="px-5 py-3 text-slate-400">{a.source === 'ais' ? 'AIS' : a.mmsi ? 'Camera + AIS' : 'Camera only'}</td>
                  <td className="px-5 py-3 font-mono text-xs text-white">{fmt(a.s_fused, 3)}</td>
                  <td className="px-5 py-3 text-slate-400 font-mono text-xs">{a.time ? a.time.slice(11, 19) : '—'}</td>
                  <td className="px-5 py-3"><span className={getStatusBadge(a.status)}>{a.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Maritime Surveillance</h2>
          <p className="text-slate-400 text-sm mt-0.5">AIS behaviour model + camera detection, fused into one alert stream</p>
        </div>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
          Auto-updating every 5s
        </div>
      </div>
      <BackendGate>
        <SourceBanner />
        <DashboardBody />
      </BackendGate>
    </div>
  )
}
