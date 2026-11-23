import { useState } from 'react'
import { Search, Filter, Download, RefreshCw, CheckCircle } from 'lucide-react'
import { useLiveData } from '../data/liveData'
import { useAppData } from '../context/AppData'
import { getSeverityBadge, getStatusBadge } from '../utils/helpers'


const severities = ['all', 'critical', 'high', 'medium', 'low']
const statuses   = ['all', 'Active', 'Reviewing', 'Resolved']

export default function AnomalyAlerts() {
  const { allAlerts } = useLiveData()
  const { refresh } = useAppData()
  const [search, setSearch]       = useState('')
  const [severity, setSeverity]   = useState('all')
  const [status, setStatus]       = useState('all')
  const [refreshed, setRefreshed] = useState(false)

  const filtered = allAlerts.filter(a => {
    const matchSearch   = a.vessel.toLowerCase().includes(search.toLowerCase()) ||
                          a.type.toLowerCase().includes(search.toLowerCase()) ||
                          a.id.toLowerCase().includes(search.toLowerCase())
    const matchSeverity = severity === 'all' || a.severity === severity
    const matchStatus   = status   === 'all' || a.status   === status
    return matchSearch && matchSeverity && matchStatus
  })

  // Export the currently filtered rows as a CSV file download
  const handleExportCSV = () => {
    const headers = ['Alert ID', 'Vessel', 'MMSI', 'Anomaly Type', 'Severity', 'Zone', 'Time', 'Status']
    const rows    = filtered.map(a =>
      [a.id, `"${a.vessel}"`, a.mmsi, `"${a.type}"`, a.severity, `"${a.zone}"`, a.time, a.status]
    )
    const csv  = [headers, ...rows].map(r => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url  = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href     = url
    link.download = `maritime-alerts-${new Date().toISOString().slice(0, 10)}.csv`
    link.click()
    URL.revokeObjectURL(url)
  }

  // Reload alerts from the backend, reset filters and show a brief confirmation
  const handleRefresh = () => {
    refresh()
    setSearch('')
    setSeverity('all')
    setStatus('all')
    setRefreshed(true)
    setTimeout(() => setRefreshed(false), 2000)
  }

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Anomaly Alerts</h2>
          <p className="text-slate-400 text-sm">{filtered.length} of {allAlerts.length} alerts shown</p>
        </div>
        <div className="flex gap-2">
          <button id="alerts-refresh" onClick={handleRefresh} className="btn-ghost">
            {refreshed
              ? <><CheckCircle className="w-4 h-4 text-green-400" /> Refreshed</>
              : <><RefreshCw className="w-4 h-4" /> Refresh</>
            }
          </button>
          <button id="alerts-export" onClick={handleExportCSV} className="btn-primary">
            <Download className="w-4 h-4" /> Export CSV
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card p-4 flex flex-wrap gap-3 items-center">
        {/* Search */}
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            id="alerts-search"
            type="text"
            placeholder="Search vessel, type, alert ID..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full bg-navy-700/50 border border-navy-600/40 text-sm text-slate-300
                       placeholder-slate-600 rounded-lg pl-9 pr-4 py-2
                       focus:outline-none focus:border-ocean-600/60 focus:ring-1 focus:ring-ocean-600/30 transition-all"
          />
        </div>

        {/* Severity filter */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <Filter className="w-3.5 h-3.5 text-slate-500" />
          <span className="label-text mr-1">Severity:</span>
          {severities.map(s => (
            <button
              key={s}
              id={`severity-filter-${s}`}
              onClick={() => setSeverity(s)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all capitalize ${
                severity === s ? 'bg-ocean-600 text-white' : 'bg-navy-700/50 text-slate-400 hover:text-white'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Status filter */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="label-text mr-1">Status:</span>
          {statuses.map(s => (
            <button
              key={s}
              id={`status-filter-${s}`}
              onClick={() => setStatus(s)}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                status === s ? 'bg-ocean-600 text-white' : 'bg-navy-700/50 text-slate-400 hover:text-white'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Alerts Table */}
      <div className="glass-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" id="anomaly-alerts-table">
            <thead>
              <tr className="border-b border-navy-600/20 bg-navy-800/40">
                {['Alert ID', 'Vessel', 'MMSI', 'Anomaly Type', 'Severity', 'Zone', 'Time', 'Status'].map(h => (
                  <th key={h} className="label-text px-5 py-3.5 text-left font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-600/15">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-12 text-slate-500">
                    No alerts match your filters.
                  </td>
                </tr>
              ) : filtered.map(a => (
                <tr key={a.id} className="table-row-hover group">
                  <td className="px-5 py-3.5 font-mono text-ocean-400 text-xs font-medium">{a.id}</td>
                  <td className="px-5 py-3.5">
                    <p className="text-white font-medium">{a.vessel}</p>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-slate-500 text-xs">{a.mmsi}</td>
                  <td className="px-5 py-3.5 text-slate-300">{a.type}</td>
                  <td className="px-5 py-3.5">
                    <span className={getSeverityBadge(a.severity) + ' capitalize'}>{a.severity}</span>
                  </td>
                  <td className="px-5 py-3.5 text-slate-400">{a.zone}</td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-400">{a.time}</td>
                  <td className="px-5 py-3.5">
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
