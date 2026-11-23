import { Link } from 'react-router-dom'
import { FlaskConical, Loader2, ServerCrash, PlayCircle } from 'lucide-react'
import { useAppData } from '../context/AppData'
import { isDemo } from '../utils/helpers'

// Shown while the first state request is pending, or when the backend cannot be reached.
export function BackendGate({ children }) {
  const { state, online, error, refresh } = useAppData()
  if (online === false && !state) {
    return (
      <div className="glass-card p-10 text-center max-w-xl mx-auto mt-16 space-y-3">
        <ServerCrash className="w-10 h-10 text-red-400 mx-auto" />
        <h3 className="section-title">Backend not reachable</h3>
        <p className="text-sm text-slate-400">
          Start the API (<span className="font-mono text-ocean-400">uvicorn fusion_api.app:app --port 8000</span> in the
          repository root) or check VITE_API_URL. A sleeping cloud server can take up to a minute to wake up.
        </p>
        <p className="text-xs text-slate-500 font-mono">{error}</p>
        <button onClick={refresh} className="btn-primary mx-auto">Retry</button>
      </div>
    )
  }
  if (!state) {
    return (
      <div className="flex items-center justify-center gap-2 text-slate-400 mt-24">
        <Loader2 className="w-5 h-5 animate-spin" /> Connecting to the analysis service…
      </div>
    )
  }
  return children
}

// Makes clear which inputs are loaded and which of them are demo / simulated data.
export function SourceBanner() {
  const { state } = useAppData()
  if (!state) return null
  const ais = state.ais?.source
  const vis = state.vision?.source
  const demo = isDemo(ais) || isDemo(vis)
  const job = state.jobs?.[0]
  return (
    <div className={`glass-card px-4 py-3 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs ${demo ? 'border-amber-500/30' : ''}`}>
      {demo && (
        <span className="flex items-center gap-1.5 text-amber-400 font-medium">
          <FlaskConical className="w-3.5 h-3.5" /> Demo scenario
        </span>
      )}
      <span className="text-slate-400">AIS: <span className="text-slate-200">{ais ?? 'no data loaded'}</span></span>
      <span className="text-slate-400">Camera: <span className="text-slate-200">{vis ?? (job ? 'processing…' : 'no video analysed')}</span></span>
      {state.detector?.fallback && (
        <span className="text-slate-500">Detector: pretrained YOLOv8 (boat class) until the vessel model is trained</span>
      )}
      {job && (
        <span className="flex items-center gap-1.5 text-ocean-400">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          {job.kind === 'demo' ? 'Analysing demo clip' : 'Analysing video'} {Math.round((job.progress || 0) * 100)}%
        </span>
      )}
    </div>
  )
}

export function EmptyState({ title, text }) {
  return (
    <div className="glass-card p-10 text-center space-y-3">
      <h3 className="section-title">{title}</h3>
      <p className="text-sm text-slate-400 max-w-lg mx-auto">{text}</p>
      <Link to="/live-analysis" className="btn-primary inline-flex">
        <PlayCircle className="w-4 h-4" /> Go to Live Analysis
      </Link>
    </div>
  )
}

export const TooltipStyle = {
  contentStyle: {
    background: '#0d1b2a',
    border: '1px solid #1a3a5c',
    borderRadius: '8px',
    fontSize: 12,
    color: '#e2e8f0',
  },
}
