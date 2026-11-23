import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Upload, FileSpreadsheet, Video, PlayCircle, Download, Loader2, CheckCircle, AlertTriangle, GitMerge, ArrowRight,
} from 'lucide-react'
import { useAppData } from '../context/AppData'
import { api, mediaUrl } from '../api'
import { BackendGate, SourceBanner } from '../components/common'
import { fmt, fmtDateTime, getVesselStatusColor } from '../utils/helpers'

function Card({ icon: Icon, title, subtitle, children, right }) {
  return (
    <div className="glass-card p-5 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-ocean-700/20 border border-ocean-600/30 flex items-center justify-center">
            <Icon className="w-4 h-4 text-ocean-400" />
          </div>
          <div>
            <h3 className="section-title text-base">{title}</h3>
            <p className="text-xs text-slate-500">{subtitle}</p>
          </div>
        </div>
        {right}
      </div>
      {children}
    </div>
  )
}

function Message({ msg }) {
  if (!msg) return null
  const ok = msg.kind === 'ok'
  return (
    <div className={`flex items-start gap-2 text-xs rounded-lg px-3 py-2 border ${ok ? 'text-green-400 bg-green-500/10 border-green-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20'}`}>
      {ok ? <CheckCircle className="w-3.5 h-3.5 mt-0.5" /> : <AlertTriangle className="w-3.5 h-3.5 mt-0.5" />}
      <span>{msg.text}</span>
    </div>
  )
}

function FilePicker({ accept, file, onFile, label }) {
  const ref = useRef(null)
  return (
    <button type="button" onClick={() => ref.current?.click()}
            className="w-full border border-dashed border-navy-600/60 hover:border-ocean-600/60 rounded-lg px-4 py-5 text-center transition-colors">
      <input ref={ref} type="file" accept={accept} className="hidden" onChange={e => onFile(e.target.files?.[0] ?? null)} />
      <Upload className="w-5 h-5 text-slate-500 mx-auto mb-1.5" />
      <p className="text-sm text-slate-300">{file ? file.name : label}</p>
      {file && <p className="text-xs text-slate-500 mt-0.5">{(file.size / 1e6).toFixed(1)} MB</p>}
    </button>
  )
}

function AisPanel() {
  const { state, uploadAis } = useAppData()
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const ais = state.ais

  const submit = async () => {
    setBusy(true); setMsg(null)
    try {
      await uploadAis(file)
      setMsg({ kind: 'ok', text: `${file.name} analysed.` })
      setFile(null)
    } catch (e) {
      setMsg({ kind: 'error', text: e.message })
    } finally { setBusy(false) }
  }

  return (
    <Card icon={FileSpreadsheet} title="AIS Trajectories" subtitle="LSTM autoencoder · sliding windows of 20 reports"
          right={<a href={api.demoCsvUrl} className="btn-ghost text-xs" download><Download className="w-3.5 h-3.5" /> Demo CSV</a>}>
      <FilePicker accept=".csv" file={file} onFile={setFile} label="Choose an AIS CSV file" />
      <p className="text-xs text-slate-500 leading-relaxed">
        Raw AIS: <span className="font-mono text-slate-400">MMSI, BaseDateTime, LAT, LON, SOG, COG</span> (optional VesselName) —
        features are derived per vessel. Or the feature format of the AIS model:
        <span className="font-mono text-slate-400"> {state.ais_model.features.join(', ')}</span>.
      </p>
      <button disabled={!file || busy} onClick={submit} className="btn-primary disabled:opacity-40">
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />} Analyse AIS
      </button>
      <Message msg={msg} />

      {ais && (
        <div className="space-y-3 pt-2 border-t border-navy-600/30">
          <div className="grid grid-cols-3 gap-3 text-center">
            {[['Vessels', ais.n_vessels], ['Anomalous', ais.n_anomalous_vessels], ['Windows > τ', ais.n_anomalous_windows]].map(([l, v]) => (
              <div key={l} className="bg-navy-700/40 rounded-lg py-2">
                <p className="text-lg font-bold text-white">{v}</p>
                <p className="label-text">{l}</p>
              </div>
            ))}
          </div>
          {ais.time_range && (
            <p className="text-xs text-slate-500">{fmtDateTime(ais.time_range[0])} → {fmtDateTime(ais.time_range[1])}</p>
          )}
          <div className="max-h-72 overflow-y-auto rounded-lg border border-navy-600/20">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-navy-800">
                <tr>{['Vessel', 'Reports', 'Max error', 'Result'].map(h => <th key={h} className="label-text px-3 py-2 text-left">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-navy-600/15">
                {ais.vessels.map(v => (
                  <tr key={v.mmsi}>
                    <td className="px-3 py-2"><p className="text-white">{v.name}</p><p className="text-slate-500">{v.mmsi}</p></td>
                    <td className="px-3 py-2 text-slate-400">{v.n_reports}</td>
                    <td className="px-3 py-2 font-mono" style={{ color: getVesselStatusColor(v.status) }}>{fmt(v.max_error, 3)}</td>
                    <td className="px-3 py-2">
                      {v.status === 'anomaly'
                        ? <span className="text-red-400">{v.anomaly_type}</span>
                        : <span className="text-slate-400 capitalize">{v.status === 'insufficient' ? `< ${ais.window_size} reports` : 'normal'}</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Card>
  )
}

function VisionPanel() {
  const { state, uploadVision, waitForJob } = useAppData()
  const cams = state.cameras
  const [camera, setCamera] = useState(Object.keys(cams)[0])
  const [start, setStart] = useState('')
  const [file, setFile] = useState(null)
  const [job, setJob] = useState(null)
  const [msg, setMsg] = useState(null)
  const [image, setImage] = useState(null)
  const vision = state.vision
  const busy = job && job.status !== 'done' && job.status !== 'error'
  const unmatched = new Set(state.alerts.filter(a => a.source === 'camera' && !a.mmsi).map(a => a.track_id))

  const submit = async () => {
    setMsg(null); setImage(null)
    try {
      const r = await uploadVision(file, camera, start)
      if (r.image) { setImage(r.image); setMsg({ kind: 'ok', text: `${r.image.detections.length} vessel(s) detected.` }); return }
      setJob(r.job)
      await waitForJob(r.job.id, setJob)
      setMsg({ kind: 'ok', text: `${file.name} analysed.` })
      setFile(null)
    } catch (e) {
      setMsg({ kind: 'error', text: e.message })
    }
  }

  return (
    <Card icon={Video} title="Camera Feed" subtitle="YOLOv8 detection · ByteTrack · zone & dwell rules">
      <div className="grid grid-cols-2 gap-3">
        <label className="text-xs text-slate-400 space-y-1">
          <span className="label-text">Camera</span>
          <select value={camera} onChange={e => setCamera(e.target.value)}
                  className="w-full bg-navy-700/60 border border-navy-600/40 text-sm text-white rounded-lg px-3 py-1.5">
            {Object.entries(cams).map(([k, c]) => <option key={k} value={k}>{c.name}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-400 space-y-1">
          <span className="label-text">Video start (UTC, optional)</span>
          <input value={start} onChange={e => setStart(e.target.value)} placeholder="2026-11-20T10:00:00Z"
                 className="w-full bg-navy-700/60 border border-navy-600/40 text-sm text-white rounded-lg px-3 py-1.5 placeholder-slate-600" />
        </label>
      </div>
      <FilePicker accept="video/*,image/*" file={file} onFile={setFile} label="Choose a video (mp4, avi, mov) or an image" />
      <p className="text-xs text-slate-500">
        Zones and ground-control points of the selected camera are scaled to the video size. Without a start time the
        clip is placed in the time range of the loaded AIS data so the two can be associated.
      </p>
      <button disabled={!file || busy} onClick={submit} className="btn-primary disabled:opacity-40">
        {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Upload className="w-4 h-4" />} Analyse video
      </button>
      {busy && (
        <div className="space-y-1">
          <div className="h-1.5 bg-navy-700 rounded-full overflow-hidden">
            <div className="h-full bg-ocean-500 transition-all" style={{ width: `${Math.round((job.progress || 0) * 100)}%` }} />
          </div>
          <p className="text-xs text-slate-500">{job.status} · {Math.round((job.progress || 0) * 100)}%</p>
        </div>
      )}
      <Message msg={msg} />

      {image && (
        <div className="space-y-2">
          <img src={mediaUrl(image.media_url)} alt="annotated" className="w-full rounded-lg border border-navy-600/30" />
          <p className="text-xs text-slate-500">
            {image.detections.filter(d => d.zones.length).length} in a restricted zone · CLAHE {image.clahe ? 'applied' : 'not needed'}
          </p>
        </div>
      )}

      {vision && !image && (
        <div className="space-y-3 pt-2 border-t border-navy-600/30">
          {vision.media_url && (
            <video key={vision.media_url} src={mediaUrl(vision.media_url)} controls autoPlay muted loop playsInline
                   className="w-full rounded-lg border border-navy-600/30 bg-black" />
          )}
          <div className="grid grid-cols-4 gap-2 text-center">
            {[['Tracks', vision.tracks.length], ['Events', vision.events.length],
              ['Frames', vision.processed_frames], ['Proc. FPS', fmt(vision.processing_fps, 1)]].map(([l, v]) => (
              <div key={l} className="bg-navy-700/40 rounded-lg py-2">
                <p className="text-base font-bold text-white">{v}</p>
                <p className="label-text">{l}</p>
              </div>
            ))}
          </div>
          <div className="max-h-56 overflow-y-auto rounded-lg border border-navy-600/20">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-navy-800">
                <tr>{['Track', 'Detections', 'Conf.', 'Rules', 's_vision', 'AIS'].map(h => <th key={h} className="label-text px-3 py-2 text-left">{h}</th>)}</tr>
              </thead>
              <tbody className="divide-y divide-navy-600/15">
                {vision.tracks.map(t => (
                  <tr key={t.track_id}>
                    <td className="px-3 py-2 font-mono text-ocean-400">#{t.track_id}</td>
                    <td className="px-3 py-2 text-slate-400">{t.n_detections}</td>
                    <td className="px-3 py-2 text-slate-300">{fmt(t.mean_conf)}</td>
                    <td className="px-3 py-2 text-slate-300">{t.reasons.length ? t.reasons.join(', ') : '—'}</td>
                    <td className="px-3 py-2 font-mono text-white">{fmt(t.s_vision)}</td>
                    <td className="px-3 py-2">{unmatched.has(t.track_id)
                      ? <span className="text-purple-400">no match</span>
                      : <span className="text-green-400">matched / ok</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Card>
  )
}

export default function LiveAnalysis() {
  const { state, loadDemo, waitForJob } = useAppData()
  const [demoMsg, setDemoMsg] = useState(null)
  const [loading, setLoading] = useState(false)

  const runDemo = async () => {
    setLoading(true); setDemoMsg(null)
    try {
      const job = await loadDemo()
      if (job) await waitForJob(job.id)
      setDemoMsg({ kind: 'ok', text: 'Demo scenario loaded: simulated AIS for the Singapore Strait + Singapore Maritime Dataset clip.' })
    } catch (e) {
      setDemoMsg({ kind: 'error', text: e.message })
    } finally { setLoading(false) }
  }

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-2xl font-bold text-white">Live Analysis</h2>
          <p className="text-slate-400 text-sm">Upload AIS data and camera footage; both branches are scored and fused automatically</p>
        </div>
        <button onClick={runDemo} disabled={loading} className="btn-primary disabled:opacity-40">
          {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <PlayCircle className="w-4 h-4" />} Load demo scenario
        </button>
      </div>
      <BackendGate>
        <SourceBanner />
        <Message msg={demoMsg} />
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
          <AisPanel />
          <VisionPanel />
        </div>
        {state && (
          <div className="glass-card p-5 flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-lg bg-purple-500/10 border border-purple-500/30 flex items-center justify-center">
                <GitMerge className="w-4 h-4 text-purple-400" />
              </div>
              <div>
                <h3 className="section-title text-base">Fusion</h3>
                <p className="text-xs text-slate-400">
                  s<sub>fused</sub> = α·s<sub>AIS</sub> + (1−α)·s<sub>vision</sub>, α = {state.settings.alpha} ·
                  camera tracks are matched to AIS within {state.settings.d_max_m} m and {state.settings.dt_s} s;
                  a track with no AIS match counts as s<sub>AIS</sub> = 1 (dark vessel)
                </p>
              </div>
            </div>
            <Link to="/anomaly-alerts" className="btn-ghost text-ocean-400">
              {state.alerts.length} fused alerts <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        )}
      </BackendGate>
    </div>
  )
}
