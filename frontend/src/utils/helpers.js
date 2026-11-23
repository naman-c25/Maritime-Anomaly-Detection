export function getSeverityBadge(severity) {
  const map = {
    critical: 'status-badge bg-red-500/15 text-red-400 border border-red-500/30',
    high:     'status-badge bg-orange-500/15 text-orange-400 border border-orange-500/30',
    medium:   'status-badge bg-amber-500/15 text-amber-400 border border-amber-500/30',
    low:      'status-badge bg-slate-500/15 text-slate-400 border border-slate-500/30',
  }
  return map[severity] ?? map.low
}

export function getStatusBadge(status) {
  const map = {
    Active:    'status-badge bg-red-500/15 text-red-400 border border-red-500/30',
    Reviewing: 'status-badge bg-amber-500/15 text-amber-400 border border-amber-500/30',
    Resolved:  'status-badge bg-green-500/15 text-green-400 border border-green-500/30',
  }
  return map[status] ?? map.Resolved
}

export function getVesselStatusColor(status) {
  const map = {
    normal:  '#10b981',
    anomaly: '#ef4444',
    dark:    '#64748b',
  }
  return map[status] ?? '#10b981'
}
