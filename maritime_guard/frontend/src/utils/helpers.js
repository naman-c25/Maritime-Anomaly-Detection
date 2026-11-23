// Fusion alert levels (advisory < warning < critical) map onto the dashboard's severity colours.
export const LEVEL_LABEL = { critical: 'Critical', warning: 'Warning', advisory: 'Advisory' }

export function getSeverityBadge(level) {
  const map = {
    critical: 'status-badge bg-red-500/15 text-red-400 border border-red-500/30',
    warning:  'status-badge bg-orange-500/15 text-orange-400 border border-orange-500/30',
    advisory: 'status-badge bg-amber-500/15 text-amber-400 border border-amber-500/30',
  }
  return map[level] ?? 'status-badge bg-slate-500/15 text-slate-400 border border-slate-500/30'
}

export function getStatusBadge(status) {
  const map = {
    Active:    'status-badge bg-red-500/15 text-red-400 border border-red-500/30',
    Reviewing: 'status-badge bg-amber-500/15 text-amber-400 border border-amber-500/30',
    Resolved:  'status-badge bg-green-500/15 text-green-400 border border-green-500/30',
  }
  return map[status] ?? map.Resolved
}

export const VESSEL_COLORS = {
  normal:  '#10b981',
  anomaly: '#ef4444',
  dark:    '#a855f7',
  camera:  '#48cae4',
  insufficient: '#64748b',
}

export function getVesselStatusColor(status) {
  return VESSEL_COLORS[status] ?? VESSEL_COLORS.normal
}

export function fmtTime(t) {
  if (t == null) return '—'
  return new Date(t * 1000).toISOString().slice(11, 19) + ' UTC'
}

export function fmtDateTime(t) {
  if (t == null) return '—'
  return new Date(t * 1000).toISOString().replace('T', ' ').slice(0, 19) + ' UTC'
}

export const fmt = (v, d = 2) => (v == null || Number.isNaN(v) ? '—' : Number(v).toFixed(d))

export const isDemo = source => Boolean(source && source.startsWith('demo'))
