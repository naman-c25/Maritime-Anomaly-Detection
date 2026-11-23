import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts'
import { Brain, ScanEye, GitMerge } from 'lucide-react'
import { useAppData } from '../context/AppData'
import { BackendGate, SourceBanner, TooltipStyle } from '../components/common'
import { fmt, getVesselStatusColor } from '../utils/helpers'

function InfoCard({ icon: Icon, title, rows, note }) {
  return (
    <div className="glass-card p-5 space-y-3">
      <div className="flex items-center gap-3 pb-3 border-b border-navy-600/30">
        <div className="w-8 h-8 rounded-lg bg-ocean-700/20 border border-ocean-600/30 flex items-center justify-center">
          <Icon className="w-4 h-4 text-ocean-400" />
        </div>
        <h3 className="section-title text-base">{title}</h3>
      </div>
      <div className="space-y-2">
        {rows.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-4 text-sm">
            <span className="text-slate-400">{k}</span>
            <span className="text-white text-right font-mono text-xs">{v}</span>
          </div>
        ))}
      </div>
      {note && <p className="text-xs text-slate-500 pt-1">{note}</p>}
    </div>
  )
}

function DetectorEvaluation({ evaluation }) {
  const runs = Object.entries(evaluation)
  if (!runs.length) {
    return (
      <p className="text-sm text-slate-500">
        No test-set evaluation yet. After training, run <span className="font-mono text-slate-400">scripts/evaluate_detector.py</span> and
        push <span className="font-mono text-slate-400">results/detector_*.json</span> — the numbers then appear here.
      </p>
    )
  }
  return runs.map(([name, r]) => (
    <div key={name} className="overflow-x-auto">
      <p className="text-xs text-slate-400 mb-2">{name}</p>
      <table className="w-full text-xs">
        <thead><tr>{['Subset', 'Precision', 'Recall', 'mAP@0.5', 'mAP@0.5:0.95'].map(h => <th key={h} className="label-text text-left py-1.5 pr-3">{h}</th>)}</tr></thead>
        <tbody className="divide-y divide-navy-600/15">
          {Object.entries(r).filter(([, v]) => v && typeof v === 'object' && 'mAP50' in v).map(([k, v]) => (
            <tr key={k}>
              <td className="py-1.5 pr-3 text-white capitalize">{k}</td>
              <td className="py-1.5 pr-3 font-mono text-slate-300">{fmt(v.precision, 3)}</td>
              <td className="py-1.5 pr-3 font-mono text-slate-300">{fmt(v.recall, 3)}</td>
              <td className="py-1.5 pr-3 font-mono text-ocean-400">{fmt(v.mAP50, 3)}</td>
              <td className="py-1.5 pr-3 font-mono text-slate-300">{fmt(v.mAP50_95, 3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {r.all?.fps && <p className="text-xs text-slate-500 mt-2">Inference speed: {fmt(r.all.fps, 1)} FPS on {r.device}</p>}
    </div>
  ))
}

function AnalyticsBody() {
  const { state } = useAppData()
  const { ais, vision, alerts, settings, detector, ais_model: model } = state
  const tau = ais?.threshold
  const perVessel = (ais?.vessels ?? []).filter(v => v.max_error != null)
    .map(v => ({ name: v.name, error: v.max_error, lg: Math.log10(Math.max(v.max_error, 1e-3)) + 3, status: v.status }))
  const lgTicks = [0, 1, 2, 3, 4, 5, 6]
  const lgLabel = v => { const e = 10 ** (v - 3); return e >= 1 ? e.toFixed(0) : e.toPrecision(1) }
  const hist = (ais?.error_histogram ?? []).map(b => ({ ...b, label: (10 ** b.log10_error).toPrecision(2) }))
  const byLevel = ['critical', 'warning', 'advisory'].map(l => ({ level: l, count: alerts.filter(a => a.level === l).length }))
  const levelColor = { critical: '#ef4444', warning: '#f97316', advisory: '#f59e0b' }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          ['AIS windows scored', ais?.n_windows?.toLocaleString() ?? '0', 'text-ocean-400'],
          ['Windows above τ', ais ? `${ais.n_anomalous_windows} (${fmt(100 * ais.n_anomalous_windows / Math.max(1, ais.n_windows), 1)}%)` : '0', 'text-red-400'],
          ['Camera detections', vision ? vision.tracks.reduce((s, t) => s + t.n_detections, 0) : 0, 'text-green-400'],
          ['Vision speed (CPU)', vision ? `${fmt(vision.processing_fps, 1)} FPS` : '—', 'text-amber-400'],
        ].map(([label, value, color]) => (
          <div key={label} className="glass-card p-5 text-center">
            <p className="label-text mb-2">{label}</p>
            <p className={`text-2xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-5">
          <h3 className="section-title mb-1">Maximum Reconstruction Error per Vessel</h3>
          <p className="text-xs text-slate-500 mb-4">Log scale · dashed line = anomaly threshold τ</p>
          <ResponsiveContainer width="100%" height={Math.max(260, perVessel.length * 24)}>
            <BarChart data={perVessel} layout="vertical" margin={{ top: 5, right: 20, left: 10, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a3a5c40" />
              <XAxis type="number" domain={[0, 6]} ticks={lgTicks} tickFormatter={lgLabel}
                     tick={{ fill: '#64748b', fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={130} interval={0} tick={{ fill: '#94a3b8', fontSize: 10 }}
                     axisLine={false} tickLine={false} />
              <Tooltip {...TooltipStyle} formatter={(v, n, item) => [fmt(item.payload.error, 4), 'max error']} />
              {tau && <ReferenceLine x={Math.log10(tau) + 3} stroke="#f59e0b" strokeDasharray="4 4"
                                     label={{ value: 'τ', fill: '#f59e0b', fontSize: 11, position: 'top' }} />}
              <Bar dataKey="lg" radius={[0, 4, 4, 0]} maxBarSize={14} isAnimationActive={false}>
                {perVessel.map(v => <Cell key={v.name} fill={getVesselStatusColor(v.status)} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="space-y-4">
          <div className="glass-card p-5">
            <h3 className="section-title mb-1">Distribution of Window Errors</h3>
            <p className="text-xs text-slate-500 mb-4">All scored AIS windows, log-spaced bins</p>
            <ResponsiveContainer width="100%" height={170}>
              <BarChart data={hist} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a3a5c40" />
                <XAxis dataKey="label" tick={{ fill: '#64748b', fontSize: 10 }} interval={3} />
                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip {...TooltipStyle} formatter={v => [v, 'windows']} labelFormatter={l => `error ≈ ${l}`} />
                <Bar dataKey="count" radius={[3, 3, 0, 0]} isAnimationActive={false}>
                  {hist.map(b => <Cell key={b.log10_error} fill={tau && 10 ** b.log10_error > tau ? '#ef4444' : '#00b4d8'} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="glass-card p-5">
            <h3 className="section-title mb-4">Fused Alerts by Level</h3>
            <div className="grid grid-cols-3 gap-3">
              {byLevel.map(l => (
                <div key={l.level} className="bg-navy-700/40 rounded-lg py-3 text-center">
                  <p className="text-2xl font-bold" style={{ color: levelColor[l.level] }}>{l.count}</p>
                  <p className="label-text capitalize">{l.level}</p>
                  <p className="text-xs text-slate-500 mt-1">≥ {fmt(settings.levels[l.level], 3)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <InfoCard icon={Brain} title="AIS Model" rows={[
          ['Architecture', `LSTM autoencoder ${model.hidden_dim}/${model.latent_dim}`],
          ['Window', `${model.window_size} reports`],
          ['Features', model.features.length],
          ['Threshold τ', fmt(model.threshold, 4)],
          ['s_AIS mapping', settings.s_ais_mapping],
        ]} note={model.features.join(' · ')} />
        <InfoCard icon={ScanEye} title="Vision Branch" rows={[
          ['Detector', detector.weights],
          ['Tracker', settings.tracker],
          ['Confidence cut-off', settings.conf],
          ['Dwell limit', `${settings.dwell_seconds} s`],
          ['Last run', vision ? `${vision.processed_frames} frames, ${vision.tracks.length} tracks` : '—'],
        ]} note={detector.note} />
        <InfoCard icon={GitMerge} title="Fusion" rows={[
          ['α (AIS weight)', fmt(settings.alpha, 2)],
          ['Gate', `${settings.d_max_m} m · ${settings.dt_s} s`],
          ['Advisory', fmt(settings.levels.advisory, 3)],
          ['Warning', fmt(settings.levels.warning, 3)],
          ['Critical', fmt(settings.levels.critical, 3)],
        ]} note="Change these on the Settings page; alerts are recomputed immediately." />
      </div>

      <div className="glass-card p-5 space-y-3">
        <h3 className="section-title">Detector Test Results</h3>
        <DetectorEvaluation evaluation={state.evaluation} />
      </div>
    </div>
  )
}

export default function Analytics() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-white">Analytics</h2>
        <p className="text-slate-400 text-sm">What the models measured on the loaded data</p>
      </div>
      <BackendGate>
        <SourceBanner />
        <AnalyticsBody />
      </BackendGate>
    </div>
  )
}
