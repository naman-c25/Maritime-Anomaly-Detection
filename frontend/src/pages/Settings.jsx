import { useState } from 'react'
import { Save, Check, Sliders, GitMerge, Database, RotateCcw, Loader2 } from 'lucide-react'
import { useAppData } from '../context/AppData'
import { api } from '../api'
import { BackendGate } from '../components/common'
import { fmt } from '../utils/helpers'

function SettingSection({ icon: Icon, title, children }) {
  return (
    <div className="glass-card p-5 space-y-4">
      <div className="flex items-center gap-3 pb-3 border-b border-navy-600/30">
        <div className="w-8 h-8 rounded-lg bg-ocean-700/20 border border-ocean-600/30 flex items-center justify-center">
          <Icon className="w-4 h-4 text-ocean-400" />
        </div>
        <h3 className="section-title">{title}</h3>
      </div>
      <div className="space-y-3">{children}</div>
    </div>
  )
}

function SettingRow({ label, description, children }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1">
      <div>
        <p className="text-sm text-white font-medium">{label}</p>
        {description && <p className="text-xs text-slate-500 mt-0.5">{description}</p>}
      </div>
      <div className="flex-shrink-0">{children}</div>
    </div>
  )
}

const inputClass = `w-28 bg-navy-700/60 border border-navy-600/40 text-sm text-white text-right
  rounded-lg px-3 py-1.5 focus:outline-none focus:border-ocean-600/60`

function SettingsBody() {
  const { state, saveSettings, loadDemo, waitForJob } = useAppData()
  const s = state.settings
  // BackendGate guarantees state is loaded, so the form starts from the server's current values.
  const [form, setForm] = useState(() => ({ alpha: s.alpha, ...s.levels, d_max_m: s.d_max_m, dt_s: s.dt_s }))
  const [saved, setSaved] = useState(false)
  const [err, setErr] = useState(null)
  const [busy, setBusy] = useState(null)
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  const save = async () => {
    setErr(null)
    try {
      await saveSettings({
        alpha: Number(form.alpha), d_max_m: Number(form.d_max_m), dt_s: Number(form.dt_s),
        levels: { advisory: Number(form.advisory), warning: Number(form.warning), critical: Number(form.critical) },
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) { setErr(e.message) }
  }

  const run = async (name, fn) => {
    setBusy(name); setErr(null)
    try {
      const job = await fn()
      if (job?.id) await waitForJob(job.id)
    } catch (e) { setErr(e.message) } finally { setBusy(null) }
  }

  return (
    <div className="space-y-5 max-w-3xl">
      <div className="flex justify-end">
        <button onClick={save} className={`btn-primary transition-colors ${saved ? 'bg-green-600 hover:bg-green-500' : ''}`}>
          {saved ? <><Check className="w-4 h-4" /> Applied</> : <><Save className="w-4 h-4" /> Apply</>}
        </button>
      </div>
      {err && <p className="text-xs text-red-400">{err}</p>}

      <SettingSection icon={GitMerge} title="Fusion">
        <SettingRow label={`AIS weight α = ${fmt(form.alpha, 2)}`}
                    description="s_fused = α·s_AIS + (1 − α)·s_vision. 1 = AIS only, 0 = camera only.">
          <input type="range" min="0" max="1" step="0.05" value={form.alpha} onChange={e => set('alpha', e.target.value)}
                 className="w-48 accent-ocean-500" />
        </SettingRow>
        <SettingRow label="Association distance (m)" description="Max. distance between a camera track and an AIS report">
          <input type="number" value={form.d_max_m} onChange={e => set('d_max_m', e.target.value)} className={inputClass} />
        </SettingRow>
        <SettingRow label="Association time window (s)" description="Max. time difference between them">
          <input type="number" value={form.dt_s} onChange={e => set('dt_s', e.target.value)} className={inputClass} />
        </SettingRow>
      </SettingSection>

      <SettingSection icon={Sliders} title="Alert Levels">
        <p className="text-xs text-slate-500">
          A vessel is alerted when its fused score reaches a level. The defaults are α × the 95th / 99th / 99.9th
          percentile of s_AIS on normal traffic; change α and you usually want to rescale these too.
        </p>
        {['advisory', 'warning', 'critical'].map(l => (
          <SettingRow key={l} label={l[0].toUpperCase() + l.slice(1)}>
            <input type="number" step="0.001" value={form[l]} onChange={e => set(l, e.target.value)} className={inputClass} />
          </SettingRow>
        ))}
      </SettingSection>

      <SettingSection icon={Database} title="Data">
        <SettingRow label="Reload demo scenario" description="Simulated Singapore Strait AIS + Singapore Maritime Dataset clip">
          <button className="btn-ghost" disabled={!!busy} onClick={() => run('demo', loadDemo)}>
            {busy === 'demo' ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />} Reload
          </button>
        </SettingRow>
        <SettingRow label="Re-run detector on the demo clip" description="Needed only if you changed weights or rules without restarting">
          <button className="btn-ghost" disabled={!!busy} onClick={() => run('rebuild', async () => (await api.rebuildDemo()).job)}>
            {busy === 'rebuild' ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />} Re-run
          </button>
        </SettingRow>
        <SettingRow label="AIS anomaly threshold τ" description="Stored with the AIS model (99th percentile of the training reconstruction errors)">
          <span className="font-mono text-sm text-white">{fmt(s.ais_threshold, 4)}</span>
        </SettingRow>
        <SettingRow label="Detector" description={state.detector.note}>
          <span className="font-mono text-sm text-white">{state.detector.weights}</span>
        </SettingRow>
      </SettingSection>
      <p className="text-xs text-slate-500">
        Changes apply to this server session. To make them permanent, edit config.yaml and push.
      </p>
    </div>
  )
}

export default function Settings() {
  return (
    <div className="space-y-5 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-white">Settings</h2>
        <p className="text-slate-400 text-sm">Fusion parameters and alert levels (applied live)</p>
      </div>
      <BackendGate><SettingsBody /></BackendGate>
    </div>
  )
}
