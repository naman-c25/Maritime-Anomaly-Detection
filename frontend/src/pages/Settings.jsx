import { useState } from 'react'
import { Save, Bell, Shield, Sliders, Radio, Database, Check } from 'lucide-react'

// NOTE: Settings are controlled React state only — no persistence or API connection exists.
// "Save Changes" logs to console; backend integration is a future phase.

const defaultSettings = {
  // Alert thresholds
  spoofing:     true,
  darkShip:     true,
  speed:        true,
  route:        false,
  // Detection sensitivity
  aiConfidence: 'Medium (80%+)',
  cooldown:     '15 minutes',
  // AIS feed
  aisLive:      true,
  replay:       false,
  aisInterval:  '30 seconds',
  // Zones
  zoneMalacca:  true,
  zoneAden:     true,
  zoneBengal:   true,
  zoneArabian:  false,
  // Data
  autoExport:   false,
  retention:    '90 days',
}

// Controlled toggle switch — uses checked + onChange (not defaultChecked)
function ToggleSwitch({ id, checked, onChange }) {
  return (
    <label id={id} className="relative inline-flex items-center cursor-pointer">
      <input
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="sr-only peer"
      />
      <div className="w-9 h-5 bg-navy-600 rounded-full peer peer-checked:bg-ocean-600
                      after:content-[''] after:absolute after:top-0.5 after:left-0.5
                      after:bg-white after:rounded-full after:h-4 after:w-4
                      after:transition-all peer-checked:after:translate-x-4" />
    </label>
  )
}

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

// Shared select styling
const selectClass = `bg-navy-700/60 border border-navy-600/40 text-sm text-white
  rounded-lg px-3 py-1.5 focus:outline-none focus:border-ocean-600/60 cursor-pointer`

export default function Settings() {
  const [settings, setSettings] = useState(defaultSettings)
  const [saved, setSaved]       = useState(false)

  const toggle = key => setSettings(prev => ({ ...prev, [key]: !prev[key] }))
  const select = (key, val) => setSettings(prev => ({ ...prev, [key]: val }))

  const handleSave = () => {
    // In production this would POST to the backend API.
    // Currently logs to console as no API is connected.
    console.log('[MaritimeGuard] Settings saved (mock):', settings)
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  return (
    <div className="space-y-5 animate-fade-in max-w-3xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Settings</h2>
          <p className="text-slate-400 text-sm">System configuration and preferences</p>
        </div>
        <button
          id="settings-save"
          onClick={handleSave}
          className={`btn-primary transition-colors ${saved ? 'bg-green-600 hover:bg-green-500' : ''}`}
        >
          {saved
            ? <><Check className="w-4 h-4" /> Saved!</>
            : <><Save className="w-4 h-4" /> Save Changes</>
          }
        </button>
      </div>

      {/* Alert Thresholds */}
      <SettingSection icon={Bell} title="Alert Thresholds">
        <SettingRow label="AIS Spoofing Alerts" description="Trigger when AIS identity mismatch detected">
          <ToggleSwitch id="toggle-spoofing" checked={settings.spoofing} onChange={() => toggle('spoofing')} />
        </SettingRow>
        <SettingRow label="Dark Ship Detection" description="Alert when vessel AIS goes silent unexpectedly">
          <ToggleSwitch id="toggle-dark-ship" checked={settings.darkShip} onChange={() => toggle('darkShip')} />
        </SettingRow>
        <SettingRow label="Speed Anomaly" description="Flag vessels exceeding expected speed thresholds">
          <ToggleSwitch id="toggle-speed" checked={settings.speed} onChange={() => toggle('speed')} />
        </SettingRow>
        <SettingRow label="Route Deviation" description="Detect vessels deviating from declared routes">
          <ToggleSwitch id="toggle-route" checked={settings.route} onChange={() => toggle('route')} />
        </SettingRow>
      </SettingSection>

      {/* Detection Sensitivity */}
      <SettingSection icon={Sliders} title="Detection Sensitivity">
        <SettingRow label="AI Confidence Threshold" description="Minimum confidence score to raise an alert">
          <select
            id="ai-confidence-select"
            value={settings.aiConfidence}
            onChange={e => select('aiConfidence', e.target.value)}
            className={selectClass}
          >
            <option>High (95%+)</option>
            <option>Medium (80%+)</option>
            <option>Low (60%+)</option>
          </select>
        </SettingRow>
        <SettingRow label="Alert Cooldown Period" description="Minimum time between repeated alerts for the same vessel">
          <select
            id="cooldown-select"
            value={settings.cooldown}
            onChange={e => select('cooldown', e.target.value)}
            className={selectClass}
          >
            <option>5 minutes</option>
            <option>15 minutes</option>
            <option>30 minutes</option>
            <option>1 hour</option>
          </select>
        </SettingRow>
      </SettingSection>

      {/* AIS Data Feed */}
      <SettingSection icon={Radio} title="AIS Data Feed">
        <SettingRow label="Live AIS Feed" description="Receive real-time vessel position updates">
          <ToggleSwitch id="toggle-ais-live" checked={settings.aisLive} onChange={() => toggle('aisLive')} />
        </SettingRow>
        <SettingRow label="Historical Replay Mode" description="Enable replay of past AIS data for analysis">
          <ToggleSwitch id="toggle-replay" checked={settings.replay} onChange={() => toggle('replay')} />
        </SettingRow>
        <SettingRow label="AIS Update Interval">
          <select
            id="ais-interval-select"
            value={settings.aisInterval}
            onChange={e => select('aisInterval', e.target.value)}
            className={selectClass}
          >
            <option>10 seconds</option>
            <option>30 seconds</option>
            <option>1 minute</option>
          </select>
        </SettingRow>
      </SettingSection>

      {/* Monitored Zones */}
      <SettingSection icon={Shield} title="Monitored Zones">
        <SettingRow label="Strait of Malacca" description="High-priority monitoring zone">
          <ToggleSwitch id="toggle-zone-malacca" checked={settings.zoneMalacca} onChange={() => toggle('zoneMalacca')} />
        </SettingRow>
        <SettingRow label="Gulf of Aden" description="Anti-piracy surveillance zone">
          <ToggleSwitch id="toggle-zone-aden" checked={settings.zoneAden} onChange={() => toggle('zoneAden')} />
        </SettingRow>
        <SettingRow label="Bay of Bengal" description="Regional monitoring zone">
          <ToggleSwitch id="toggle-zone-bengal" checked={settings.zoneBengal} onChange={() => toggle('zoneBengal')} />
        </SettingRow>
        <SettingRow label="Arabian Sea" description="Extended patrol zone">
          <ToggleSwitch id="toggle-zone-arabian" checked={settings.zoneArabian} onChange={() => toggle('zoneArabian')} />
        </SettingRow>
      </SettingSection>

      {/* Data & Export */}
      <SettingSection icon={Database} title="Data & Export">
        <SettingRow label="Auto-export Reports" description="Daily anomaly summary sent at midnight UTC">
          <ToggleSwitch id="toggle-auto-export" checked={settings.autoExport} onChange={() => toggle('autoExport')} />
        </SettingRow>
        <SettingRow label="Data Retention Period">
          <select
            id="retention-select"
            value={settings.retention}
            onChange={e => select('retention', e.target.value)}
            className={selectClass}
          >
            <option>30 days</option>
            <option>90 days</option>
            <option>1 year</option>
          </select>
        </SettingRow>
      </SettingSection>
    </div>
  )
}
