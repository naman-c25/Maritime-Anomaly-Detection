import { useEffect, useMemo, useRef, useState } from 'react'
import { MapContainer, TileLayer, CircleMarker, Polyline, Polygon, Popup, Tooltip as MapTip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { Wifi, AlertTriangle, Camera, EyeOff } from 'lucide-react'
import { useAppData } from '../context/AppData'
import { BackendGate, SourceBanner } from '../components/common'
import { getVesselStatusColor, VESSEL_COLORS, fmt, fmtTime } from '../utils/helpers'

const FILTERS = ['all', 'normal', 'anomaly', 'dark', 'camera']

// Fits the map to all vessels once, then flies to the selected vessel.
function MapController({ bounds, selected }) {
  const map = useMap()
  const fitted = useRef(false)
  useEffect(() => {
    if (!fitted.current && bounds.length > 1) {
      map.fitBounds(bounds, { padding: [30, 30] })
      fitted.current = true
    }
  }, [bounds, map])
  useEffect(() => {
    if (selected) map.flyTo([selected.lat, selected.lon], 14, { duration: 1.2 })
  }, [selected, map])
  return null
}

function useItems(state) {
  return useMemo(() => {
    const items = []
    for (const v of state.ais?.vessels ?? []) {
      if (v.lat == null) continue
      items.push({ key: `ais-${v.mmsi}`, kind: 'ais', status: v.status === 'anomaly' ? 'anomaly' : 'normal',
                   name: v.name, sub: `MMSI ${v.mmsi}`, lat: v.lat, lon: v.lon, path: v.track, v })
    }
    const dark = new Set(state.alerts.filter(a => a.source === 'camera' && !a.mmsi).map(a => a.track_id))
    for (const t of state.vision?.tracks ?? []) {
      if (t.lat == null) continue
      const isDark = dark.has(t.track_id)
      items.push({ key: `cam-${t.track_id}`, kind: 'camera', status: isDark ? 'dark' : 'camera',
                   name: `Camera track #${t.track_id}`, sub: isDark ? 'no AIS match' : 'matched to AIS',
                   lat: t.lat, lon: t.lon, path: t.path, t })
    }
    return items
  }, [state])
}

function StatusIcon({ status }) {
  if (status === 'anomaly') return <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
  if (status === 'dark') return <EyeOff className="w-3.5 h-3.5 text-purple-400" />
  if (status === 'camera') return <Camera className="w-3.5 h-3.5 text-ocean-400" />
  return <Wifi className="w-3.5 h-3.5 text-green-400" />
}

function TrackingBody() {
  const { state } = useAppData()
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('all')
  const items = useItems(state)
  const shown = filter === 'all' ? items : items.filter(i => i.status === filter)
  const bounds = useMemo(() => items.map(i => [i.lat, i.lon]), [items])
  const cameras = Object.values(state.cameras).filter(c => c.position)
  const counts = Object.fromEntries(FILTERS.map(f => [f, f === 'all' ? items.length : items.filter(i => i.status === f).length]))

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-2 flex-wrap">
        {FILTERS.map(f => (
          <button key={f} onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all capitalize ${
                    filter === f ? 'bg-ocean-600 text-white' : 'bg-navy-700/50 text-slate-400 hover:text-white border border-navy-600/30'}`}>
            {f} ({counts[f]})
          </button>
        ))}
        <div className="flex items-center gap-4 ml-auto text-xs text-slate-400">
          {[['AIS normal', VESSEL_COLORS.normal], ['AIS anomaly', VESSEL_COLORS.anomaly], ['Camera, matched', VESSEL_COLORS.camera],
            ['Camera, no AIS', VESSEL_COLORS.dark], ['Restricted zone', '#ef4444']].map(([l, c]) => (
            <span key={l} className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full" style={{ background: c }} />{l}</span>
          ))}
        </div>
      </div>

      <div className="flex gap-4" style={{ height: 'calc(100vh - 260px)', minHeight: 480 }}>
        <div className="flex-1 glass-card overflow-hidden">
          <MapContainer center={[1.25, 103.86]} zoom={11} style={{ height: '100%', width: '100%' }} className="rounded-xl">
            <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
                       url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            <MapController bounds={bounds} selected={selected} />

            {cameras.map(c => (
              <CircleMarker key={c.name} center={c.position} radius={6}
                            pathOptions={{ color: '#ffffff', fillColor: '#0096c7', fillOpacity: 1, weight: 2 }}>
                <MapTip direction="top">{c.name}</MapTip>
              </CircleMarker>
            ))}
            {cameras.flatMap(c => c.zones).map(z => (
              <Polygon key={z.name} positions={z.polygon} pathOptions={{ color: '#ef4444', weight: 2, fillOpacity: 0.15 }}>
                <MapTip>{z.name}</MapTip>
              </Polygon>
            ))}

            {shown.map(i => i.path?.length > 1 && (
              <Polyline key={`${i.key}-path`} positions={i.path}
                        pathOptions={{ color: getVesselStatusColor(i.status), weight: selected?.key === i.key ? 3 : 1.5,
                                       opacity: selected && selected.key !== i.key ? 0.25 : 0.7 }} />
            ))}
            {shown.map(i => (
              <CircleMarker key={i.key} center={[i.lat, i.lon]}
                            radius={i.status === 'anomaly' || i.status === 'dark' ? 9 : 6}
                            pathOptions={{ color: getVesselStatusColor(i.status), fillColor: getVesselStatusColor(i.status),
                                           fillOpacity: 0.85, weight: selected?.key === i.key ? 3 : 1 }}
                            eventHandlers={{ click: () => setSelected(i) }}>
                <Popup>
                  <div className="text-xs space-y-1" style={{ minWidth: 190 }}>
                    <p className="font-semibold text-sm">{i.name}</p>
                    <p className="text-slate-500">{i.sub}</p>
                    {i.v && (
                      <div className="grid grid-cols-2 gap-1 mt-2">
                        <span className="text-slate-500">Type:</span><span>{i.v.type ?? '—'}</span>
                        <span className="text-slate-500">Speed:</span><span>{fmt(i.v.sog, 1)} kn</span>
                        <span className="text-slate-500">Course:</span><span>{fmt(i.v.cog, 0)}°</span>
                        <span className="text-slate-500">Max error:</span><span>{fmt(i.v.max_error, 3)}</span>
                        <span className="text-slate-500">Last report:</span><span>{fmtTime(i.v.last_t)}</span>
                      </div>
                    )}
                    {i.t && (
                      <div className="grid grid-cols-2 gap-1 mt-2">
                        <span className="text-slate-500">Detections:</span><span>{i.t.n_detections}</span>
                        <span className="text-slate-500">Confidence:</span><span>{fmt(i.t.mean_conf)}</span>
                        <span className="text-slate-500">s_vision:</span><span>{fmt(i.t.s_vision)}</span>
                        <span className="text-slate-500">Rules:</span><span>{i.t.reasons.join(', ') || '—'}</span>
                      </div>
                    )}
                    {i.v?.anomaly_type && <p className="mt-2 font-medium" style={{ color: '#ef4444' }}>{i.v.anomaly_type}</p>}
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        <div className="w-72 flex-shrink-0 glass-card flex flex-col">
          <div className="px-4 py-3 border-b border-navy-600/30">
            <h3 className="section-title text-base">Vessels</h3>
            <p className="text-xs text-slate-500 mt-0.5">Click to locate on the map</p>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-navy-600/15">
            {shown.length === 0 && <p className="px-4 py-6 text-xs text-slate-500 text-center">Nothing to show.</p>}
            {shown.map(i => (
              <div key={i.key} onClick={() => setSelected(selected?.key === i.key ? null : i)}
                   className={`px-4 py-3 cursor-pointer transition-colors ${selected?.key === i.key ? 'bg-ocean-700/20' : 'hover:bg-navy-700/30'}`}>
                <div className="flex items-center gap-2 min-w-0">
                  <StatusIcon status={i.status} />
                  <div className="min-w-0">
                    <p className="text-white text-xs font-medium truncate">{i.name}</p>
                    <p className="text-slate-500 text-xs">{i.sub}</p>
                  </div>
                </div>
                <p className="mt-1 ml-5 text-xs text-slate-500">
                  {i.v ? `${i.v.type ?? 'Vessel'} · ${fmt(i.v.sog, 1)} kn · ${i.v.anomaly_type ?? 'normal behaviour'}`
                       : `${i.t.n_detections} detections · ${i.t.reasons.join(', ') || 'no rule triggered'}`}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default function VesselTracking() {
  return (
    <div className="flex flex-col gap-4 h-full animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-white">Vessel Tracking</h2>
        <p className="text-slate-400 text-sm">Last AIS position and track of every vessel, plus camera tracks projected onto the chart</p>
      </div>
      <BackendGate>
        <SourceBanner />
        <TrackingBody />
      </BackendGate>
    </div>
  )
}
