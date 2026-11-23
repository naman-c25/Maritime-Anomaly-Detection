import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, CircleMarker, Popup, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { vessels } from '../data/mockData'
import { getVesselStatusColor } from '../utils/helpers'
import { Ship, Wifi, WifiOff, AlertTriangle } from 'lucide-react'

const statusIcon = { normal: '🟢', anomaly: '🔴', dark: '⚫' }

// Renders nothing — just commands the Leaflet map instance to fly to the selected vessel.
// Must be placed inside <MapContainer> so that useMap() can access the map context.
function MapFlyTo({ vessel }) {
  const map = useMap()
  useEffect(() => {
    if (vessel) {
      map.flyTo([vessel.lat, vessel.lng], 7, { animate: true, duration: 1.5 })
    }
  }, [vessel, map])
  return null
}

export default function VesselTracking() {
  const [selected, setSelected] = useState(null)
  const [filter, setFilter] = useState('all')

  const filtered = filter === 'all' ? vessels : vessels.filter(v => v.status === filter)

  return (
    <div className="flex flex-col gap-4 h-full animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Vessel Tracking</h2>
          <p className="text-slate-400 text-sm">Live AIS feed — {vessels.length} vessels in range</p>
        </div>
        {/* Filter Buttons */}
        <div className="flex gap-2" id="vessel-filter-controls">
          {['all','normal','anomaly','dark'].map(f => (
            <button
              key={f}
              id={`filter-${f}`}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all capitalize ${
                filter === f
                  ? 'bg-ocean-600 text-white'
                  : 'bg-navy-700/50 text-slate-400 hover:text-white border border-navy-600/30'
              }`}
            >
              {f === 'all' ? `All (${vessels.length})` : f}
            </button>
          ))}
        </div>
      </div>

      <div className="flex gap-4 flex-1 min-h-0">
        {/* Map */}
        <div className="flex-1 glass-card overflow-hidden">
          <MapContainer
            center={[10, 70]}
            zoom={4}
            style={{ height: '100%', width: '100%', minHeight: '500px' }}
            className="rounded-xl"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            {/* Fly to selected vessel when sidebar item is clicked */}
            <MapFlyTo vessel={selected} />
            {filtered.map(v => (
              <CircleMarker
                key={v.id}
                center={[v.lat, v.lng]}
                radius={v.status === 'anomaly' ? 10 : 7}
                pathOptions={{
                  color: getVesselStatusColor(v.status),
                  fillColor: getVesselStatusColor(v.status),
                  fillOpacity: 0.8,
                  weight: v.status === 'anomaly' ? 2 : 1,
                }}
                eventHandlers={{ click: () => setSelected(v) }}
              >
                <Popup className="maritime-popup">
                  <div className="text-xs space-y-1 p-1" style={{ minWidth: 180 }}>
                    <p className="font-semibold text-sm">{v.name}</p>
                    <p className="text-slate-500">MMSI: {v.mmsi}</p>
                    <div className="grid grid-cols-2 gap-1 mt-2 text-xs">
                      <span className="text-slate-500">Type:</span><span>{v.type}</span>
                      <span className="text-slate-500">Flag:</span><span>{v.flag}</span>
                      <span className="text-slate-500">Speed:</span><span>{v.speed} kn</span>
                      <span className="text-slate-500">HDG:</span><span>{v.heading}°</span>
                    </div>
                    <div className="mt-2 pt-2 border-t border-slate-200">
                      <span style={{ color: getVesselStatusColor(v.status) }} className="font-medium capitalize">
                        {statusIcon[v.status]} {v.status}
                      </span>
                    </div>
                  </div>
                </Popup>
              </CircleMarker>
            ))}
          </MapContainer>
        </div>

        {/* Vessel List Panel */}
        <div className="w-72 flex-shrink-0 glass-card flex flex-col">
          <div className="px-4 py-3 border-b border-navy-600/30">
            <h3 className="section-title text-base">Vessel List</h3>
            <p className="text-xs text-slate-500 mt-0.5">Click to highlight on map</p>
          </div>
          <div className="flex-1 overflow-y-auto divide-y divide-navy-600/15">
            {filtered.map(v => (
              <div
                key={v.id}
                id={`vessel-row-${v.id}`}
                onClick={() => setSelected(selected?.id === v.id ? null : v)}
                className={`px-4 py-3 cursor-pointer transition-colors ${
                  selected?.id === v.id ? 'bg-ocean-700/20' : 'hover:bg-navy-700/30'
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-sm flex-shrink-0" title={v.status}>
                      {v.status === 'normal' ? (
                        <Wifi className="w-3.5 h-3.5 text-green-400" />
                      ) : v.status === 'dark' ? (
                        <WifiOff className="w-3.5 h-3.5 text-slate-500" />
                      ) : (
                        <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                      )}
                    </span>
                    <div className="min-w-0">
                      <p className="text-white text-xs font-medium truncate">{v.name}</p>
                      <p className="text-slate-500 text-xs">{v.mmsi}</p>
                    </div>
                  </div>
                  <span className="text-slate-500 text-xs flex-shrink-0">{v.lastSeen}</span>
                </div>
                <div className="flex items-center gap-3 mt-1.5 ml-5 text-xs text-slate-500">
                  <span>{v.type}</span>
                  <span>·</span>
                  <span>{v.speed} kn</span>
                  <span>·</span>
                  <span>HDG {v.heading}°</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
