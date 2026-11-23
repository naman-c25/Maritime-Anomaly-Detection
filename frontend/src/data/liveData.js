// Turns the backend state (/api/state) into the same data shapes the pages used from mockData.js,
// so the original UI stays unchanged and only the numbers become real.
import { useMemo } from 'react'
import { useAppData } from '../context/AppData'

const LEVEL_TO_SEVERITY = { critical: 'critical', warning: 'high', advisory: 'medium' }
const PIE_COLORS = ['#00b4d8', '#0096c7', '#48cae4', '#0077b6', '#90e0ef', '#0369a1', '#7dd3fc', '#0e7490']

// Flag state from the MMSI's Maritime Identification Digits (first 3 digits; AtoN MMSIs start with 99).
const MID = {
  201: 'AL', 205: 'BE', 209: 'CY', 210: 'CY', 211: 'DE', 212: 'CY', 215: 'MT', 218: 'DE', 219: 'DK', 220: 'DK',
  224: 'ES', 225: 'ES', 226: 'FR', 227: 'FR', 228: 'FR', 229: 'MT', 232: 'GB', 233: 'GB', 234: 'GB', 235: 'GB',
  236: 'GI', 237: 'GR', 239: 'GR', 240: 'GR', 241: 'GR', 244: 'NL', 245: 'NL', 246: 'NL', 247: 'IT', 248: 'MT',
  249: 'MT', 255: 'PT', 256: 'MT', 257: 'NO', 258: 'NO', 259: 'NO', 261: 'PL', 265: 'SE', 266: 'SE', 271: 'TR',
  273: 'RU', 304: 'AG', 305: 'AG', 308: 'BS', 309: 'BS', 310: 'BM', 311: 'BS', 312: 'BZ', 314: 'BB', 316: 'CA',
  319: 'KY', 338: 'US', 351: 'PA', 352: 'PA', 353: 'PA', 354: 'PA', 355: 'PA', 356: 'PA', 357: 'PA', 366: 'US',
  367: 'US', 368: 'US', 369: 'US', 370: 'PA', 371: 'PA', 372: 'PA', 373: 'PA', 374: 'PA', 375: 'VC', 376: 'VC',
  377: 'VC', 403: 'SA', 412: 'CN', 413: 'CN', 414: 'CN', 416: 'TW', 419: 'IN', 422: 'IR', 431: 'JP', 432: 'JP',
  440: 'KR', 441: 'KR', 447: 'KW', 461: 'OM', 463: 'PK', 466: 'QA', 470: 'AE', 471: 'AE', 477: 'HK', 503: 'AU',
  508: 'BN', 512: 'NZ', 518: 'CK', 525: 'ID', 533: 'MY', 538: 'MH', 548: 'PH', 563: 'SG', 564: 'SG', 565: 'SG',
  566: 'SG', 567: 'TH', 574: 'VN', 576: 'VU', 577: 'VU', 620: 'KM', 636: 'LR', 637: 'LR', 667: 'SL', 671: 'TG',
}

function flagOf(mmsi) {
  const s = String(mmsi ?? '')
  const mid = s.startsWith('99') || s.startsWith('98') ? s.slice(2, 5) : s.slice(0, 3)
  return MID[mid] ?? '—'
}

const hhmm = t => (t == null ? '—' : new Date(t * 1000).toISOString().slice(11, 16) + ' UTC')

function ago(t, ref) {
  if (t == null || ref == null) return '—'
  const m = Math.max(0, Math.round((ref - t) / 60))
  if (m < 60) return `${m}m ago`
  if (m < 1440) return `${Math.round(m / 60)}h ago`
  return `${Math.round(m / 1440)}d ago`
}

function zoneOf(a) {
  if (a.source === 'camera') {
    const m = /restricted-zone entry \(([^)]+)\)/.exec(a.reason || '')
    return m ? m[1] : 'Camera view'
  }
  return a.lat != null ? `${a.lat.toFixed(3)}°, ${a.lon.toFixed(3)}°` : '—'
}

export function buildLiveData(state) {
  const ais = state?.ais
  const vision = state?.vision
  const alertsRaw = state?.alerts ?? []
  const aisVessels = ais?.vessels ?? []
  const tracks = vision?.tracks ?? []
  const darkAlerts = alertsRaw.filter(a => a.source === 'camera' && !a.mmsi)
  const darkIds = new Set(darkAlerts.map(a => a.track_id))
  const refT = Math.max(ais?.time_range?.[1] ?? 0, ...tracks.map(t => t.last_t ?? 0)) || null

  // ── alerts (same shape as recentAlerts / allAlerts) ──
  const allAlerts = alertsRaw.map(a => ({
    id: a.id,
    vessel: a.name,
    mmsi: a.mmsi ?? 'no AIS',
    type: a.type,
    severity: LEVEL_TO_SEVERITY[a.level] ?? 'low',
    zone: zoneOf(a),
    time: a.time ? a.time.slice(11, 16) + ' UTC' : '—',
    status: a.status,
  }))
  const recentAlerts = allAlerts.slice(0, 6)

  // ── KPI cards ──
  const zones = Object.values(state?.cameras ?? {}).reduce((n, c) => n + (c.zones?.length ?? 0), 0)
  const nCams = Object.values(state?.cameras ?? {}).filter(c => c.zones?.length).length
  const evalRun = Object.values(state?.evaluation ?? {})[0]
  const critical = alertsRaw.filter(a => a.level === 'critical').length
  const kpiData = [
    { id: 'active-vessels', label: 'Active Vessels', value: String(aisVessels.length + darkIds.size),
      delta: `${tracks.length} seen by camera`, deltaUp: true, icon: 'Ship', color: 'ocean' },
    { id: 'anomalies-detected', label: 'Anomalies Detected', value: String(alertsRaw.length),
      delta: `${critical} critical`, deltaUp: false, icon: 'AlertTriangle', color: 'red' },
    { id: 'zones-monitored', label: 'Zones Monitored', value: String(zones),
      delta: `${nCams} camera${nCams === 1 ? '' : 's'} online`, deltaUp: true, icon: 'MapPin', color: 'green' },
    evalRun?.all
      ? { id: 'ai-model-accuracy', label: 'Detector mAP@0.5', value: `${(100 * evalRun.all.mAP50).toFixed(1)}%`,
          delta: 'on unseen test videos', deltaUp: true, icon: 'Cpu', color: 'amber' }
      : { id: 'ai-model-accuracy', label: 'AIS Windows Flagged',
          value: ais ? `${(100 * ais.n_anomalous_windows / Math.max(1, ais.n_windows)).toFixed(1)}%` : '0%',
          delta: `of ${ais?.n_windows ?? 0} windows scored`, deltaUp: false, icon: 'Cpu', color: 'amber' },
  ]

  // ── anomaly trend (same keys as before: spoofing, darkShip, speedAnomaly, unauthorized) ──
  const anomalyTrend = state?.trend ?? []

  // ── vessels by type (pie) ──
  const typeCount = {}
  aisVessels.forEach(v => { const t = v.type || 'Unknown'; typeCount[t] = (typeCount[t] || 0) + 1 })
  if (darkIds.size) typeCount['No AIS (camera)'] = darkIds.size
  const vesselsByType = Object.entries(typeCount).sort((a, b) => b[1] - a[1])
    .map(([name, value], i) => ({ name, value, color: PIE_COLORS[i % PIE_COLORS.length] }))

  // ── vessels on the map ──
  const vessels = aisVessels.filter(v => v.lat != null).map(v => ({
    id: v.mmsi, name: v.name, mmsi: v.mmsi, type: v.type || '—', flag: flagOf(v.mmsi),
    lat: v.lat, lng: v.lon, speed: v.sog, heading: Math.round(v.cog ?? 0),
    status: v.status === 'anomaly' ? 'anomaly' : 'normal', lastSeen: ago(v.last_t, refT),
  }))
  tracks.filter(t => darkIds.has(t.track_id) && t.lat != null).forEach(t => vessels.push({
    id: `CAM-${t.track_id}`, name: `Unidentified vessel #${t.track_id}`, mmsi: 'no AIS', type: 'Camera detection',
    flag: '—', lat: t.lat, lng: t.lon, speed: '—', heading: '—', status: 'dark', lastSeen: ago(t.last_t, refT),
  }))

  // ── analytics ──
  const weeklyAnomalies = aisVessels.filter(v => v.anomalous_windows > 0)
    .sort((a, b) => b.anomalous_windows - a.anomalous_windows).slice(0, 7)
    .map(v => ({ day: v.name, count: v.anomalous_windows }))
  const byType = {}
  aisVessels.forEach(v => {
    const t = v.type || 'Unknown'
    byType[t] = byType[t] || { w: 0, a: 0 }
    byType[t].w += v.n_windows || 0
    byType[t].a += v.anomalous_windows || 0
  })
  const zoneRiskData = Object.entries(byType).map(([zone, { w, a }]) => ({ zone, risk: w ? Math.round(100 * a / w) : 0 }))

  const visDetections = tracks.reduce((s, t) => s + t.n_detections, 0)
  const meanConf = visDetections ? tracks.reduce((s, t) => s + t.mean_conf * t.n_detections, 0) / visDetections : 0
  const summary = [
    { label: 'Total Anomalies', value: String(alertsRaw.length), color: 'text-red-400' },
    { label: 'Windows Above τ', value: ais ? `${(100 * ais.n_anomalous_windows / Math.max(1, ais.n_windows)).toFixed(1)}%` : '—', color: 'text-amber-400' },
    { label: 'Vision Speed (CPU)', value: vision?.processing_fps ? `${vision.processing_fps.toFixed(1)} FPS` : '—', color: 'text-ocean-400' },
  ]
  const performance = evalRun?.all
    ? { title: 'Detector Performance (test set)', rows: [
        { metric: 'Precision', value: 100 * evalRun.all.precision, color: '#00b4d8' },
        { metric: 'Recall', value: 100 * evalRun.all.recall, color: '#10b981' },
        { metric: 'mAP@0.5', value: 100 * evalRun.all.mAP50, color: '#f59e0b' },
        { metric: 'mAP@0.5:0.95', value: 100 * evalRun.all.mAP50_95, color: '#a855f7' },
      ] }
    : { title: 'AI Model Statistics (loaded data)', rows: [
        { metric: 'AIS windows within τ', value: ais ? 100 * (1 - ais.n_anomalous_windows / Math.max(1, ais.n_windows)) : 0, color: '#00b4d8' },
        { metric: 'Vessels flagged by AIS model', value: ais ? 100 * ais.n_anomalous_vessels / Math.max(1, ais.n_vessels) : 0, color: '#10b981' },
        { metric: 'Detector mean confidence', value: 100 * meanConf, color: '#f59e0b' },
        { metric: 'Camera tracks matched to AIS', value: tracks.length ? 100 * (1 - darkIds.size / tracks.length) : 0, color: '#a855f7' },
      ] }

  return { kpiData, recentAlerts, allAlerts, anomalyTrend, vesselsByType, vessels, weeklyAnomalies, zoneRiskData,
           summary, performance, hhmm }
}

export function useLiveData() {
  const { state } = useAppData()
  return useMemo(() => buildLiveData(state), [state])
}
