import { Fragment, useState } from 'react'
import { Search, Filter, Download, RefreshCw, CheckCircle, ChevronDown, ChevronRight } from 'lucide-react'
import { useAppData } from '../context/AppData'
import { BackendGate, SourceBanner } from '../components/common'
import { getSeverityBadge, getStatusBadge, LEVEL_LABEL, fmt } from '../utils/helpers'

const levels   = ['all', 'critical', 'warning', 'advisory']
const statuses = ['all', 'Active', 'Reviewing', 'Resolved']
const sources  = ['all', 'camera', 'ais']

function ScoreBar({ value, color }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-14 h-1.5 bg-navy-700 rounded-full overflow-hidden">
        <div className="h-full rounded-full" style={{ width: `${Math.min(100, value * 100)}%`, background: color }} />
      </div>
      <span className="font-mono text-xs text-slate-300">{fmt(value, 2)}</span>
    </div>
  )
}

function AlertsBody() {
  const { state, setAlertStatus, refresh } = useAppData()
  const alerts = state.alerts
  const [search, setSearch] = useState('')
  const [level, setLevel] = useState('all')
  const [status, setStatus] = useState('all')
  const [source, setSource] = useState('all')
  const [open, setOpen] = useState(null)
  const [refreshed, setRefreshed] = useState(false)

  const q = search.toLowerCase()
  const filtered = alerts.filter(a =>
    (a.name.toLowerCase().includes(q) || a.type.toLowerCase().includes(q) || a.id.toLowerCase().includes(q) ||
     String(a.mmsi ?? '').includes(q)) &&
    (level === 'all' || a.level === level) &&
    (status === 'all' || a.status === status) &&
    (source === 'all' || a.source === source))

  const exportCsv = () => {
    const headers = ['Alert ID', 'Vessel', 'MMSI', 'Type', 'Level', 'Source', 's_AIS', 's_vision', 's_fused', 'Lat', 'Lon', 'Time', 'Status', 'Reason']
    const rows = filtered.map(a => [a.id, `"${a.name}"`, a.mmsi ?? '', `"${a.type}"`, a.level, a.source, a.s_ais, a.s_vision,
                                    a.s_fused, a.lat ?? '', a.lon ?? '', a.time ?? '', a.status, `"${a.reason}"`])
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
    const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8;' }))
    const link = document.createElement('a')
    link.href = url
    link.download = `maritime-alerts-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  const doRefresh = async () => {
    await refresh()
    setRefreshed(true)
    setTimeout(() => setRefreshed(false), 2000)
  }

  const chip = (value, current, set) => (
    <button key={value} onClick={() => set(value)}
            className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all capitalize ${
              current === value ? 'bg-ocean-600 text-white' : 'bg-navy-700/50 text-slate-400 hover:text-white'}`}>
      {value === 'ais' ? 'AIS' : value}
    </button>
  )

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <p className="text-slate-400 text-sm">{filtered.length} of {alerts.length} alerts shown</p>
        <div className="flex gap-2">
          <button onClick={doRefresh} className="btn-ghost">
            {refreshed ? <><CheckCircle className="w-4 h-4 text-green-400" /> Refreshed</> : <><RefreshCw className="w-4 h-4" /> Refresh</>}
          </button>
          <button onClick={exportCsv} className="btn-primary"><Download className="w-4 h-4" /> Export CSV</button>
        </div>
      </div>

      <div className="glass-card p-4 flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input type="text" placeholder="Search vessel, MMSI, type, alert ID..." value={search} onChange={e => setSearch(e.target.value)}
                 className="w-full bg-navy-700/50 border border-navy-600/40 text-sm text-slate-300 placeholder-slate-600 rounded-lg pl-9 pr-4 py-2
                            focus:outline-none focus:border-ocean-600/60 focus:ring-1 focus:ring-ocean-600/30 transition-all" />
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <span className="label-text mr-1">Level:</span>
          {levels.map(v => chip(v, level, setLevel))}
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="label-text mr-1">Source:</span>
          {sources.map(v => chip(v, source, setSource))}
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="label-text mr-1">Status:</span>
          {statuses.map(v => chip(v, status, setStatus))}
        </div>
      </div>

      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-navy-600/20 bg-navy-800/40">
                {['', 'Alert ID', 'Vessel', 'Type', 'Level', 's_AIS', 's_vision', 's_fused', 'Time', 'Status'].map(h => (
                  <th key={h} className="label-text px-4 py-3.5 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-600/15">
              {filtered.length === 0 ? (
                <tr><td colSpan={10} className="text-center py-12 text-slate-500">No alerts match your filters.</td></tr>
              ) : filtered.map(a => (
                <Fragment key={a.id}>
                  <tr className="table-row-hover" onClick={() => setOpen(open === a.id ? null : a.id)}>
                    <td className="pl-4 text-slate-500">{open === a.id ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}</td>
                    <td className="px-4 py-3.5 font-mono text-ocean-400 text-xs font-medium">{a.id}</td>
                    <td className="px-4 py-3.5">
                      <p className="text-white font-medium">{a.name}</p>
                      <p className="text-slate-500 text-xs">{a.mmsi ? `MMSI ${a.mmsi}` : 'no AIS identity'}</p>
                    </td>
                    <td className="px-4 py-3.5 text-slate-300">{a.type}</td>
                    <td className="px-4 py-3.5"><span className={getSeverityBadge(a.level)}>{LEVEL_LABEL[a.level]}</span></td>
                    <td className="px-4 py-3.5"><ScoreBar value={a.s_ais} color="#f59e0b" /></td>
                    <td className="px-4 py-3.5"><ScoreBar value={a.s_vision} color="#48cae4" /></td>
                    <td className="px-4 py-3.5"><ScoreBar value={a.s_fused} color="#ef4444" /></td>
                    <td className="px-4 py-3.5 font-mono text-xs text-slate-400">{a.time ? a.time.slice(11, 19) : '—'}</td>
                    <td className="px-4 py-3.5" onClick={e => e.stopPropagation()}>
                      <select value={a.status} onChange={e => setAlertStatus(a.id, e.target.value)}
                              className={`${getStatusBadge(a.status)} bg-transparent cursor-pointer focus:outline-none`}>
                        {statuses.slice(1).map(s => <option key={s} value={s} className="bg-navy-800 text-white">{s}</option>)}
                      </select>
                    </td>
                  </tr>
                  {open === a.id && (
                    <tr className="bg-navy-800/40">
                      <td />
                      <td colSpan={9} className="px-4 py-3 text-xs text-slate-400 space-y-1">
                        <p><span className="label-text mr-2">Evidence</span>{a.reason}</p>
                        <p>
                          <span className="label-text mr-2">Source</span>
                          {a.source === 'camera' ? `camera track #${a.track_id}` : 'AIS only (outside camera view)'}
                          {a.lat != null && <> · position {fmt(a.lat, 5)}, {fmt(a.lon, 5)}</>}
                          {a.time && <> · {a.time.replace('T', ' ').replace('Z', ' UTC')}</>}
                        </p>
                        <p>
                          <span className="label-text mr-2">Score</span>
                          {fmt(state.settings.alpha, 2)} × {fmt(a.s_ais, 3)} + {fmt(1 - state.settings.alpha, 2)} × {fmt(a.s_vision, 3)} = {fmt(a.s_fused, 3)}
                        </p>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default function AnomalyAlerts() {
  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-white">Anomaly Alerts</h2>
        <p className="text-slate-400 text-sm">One alert per vessel whose fused score reaches the advisory level — click a row for the evidence</p>
      </div>
      <BackendGate>
        <SourceBanner />
        <AlertsBody />
      </BackendGate>
    </div>
  )
}
