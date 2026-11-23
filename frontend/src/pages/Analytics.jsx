import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, RadarChart, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, Radar, Legend,
} from 'recharts'
import { weeklyAnomalies, zoneRiskData, anomalyTrend } from '../data/mockData'

const TooltipStyle = {
  contentStyle: {
    background: '#0d1b2a',
    border: '1px solid #1a3a5c',
    borderRadius: '8px',
    fontSize: 12,
    color: '#e2e8f0',
  }
}

export default function Analytics() {
  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white">Analytics</h2>
        <p className="text-slate-400 text-sm">AI model performance and anomaly intelligence</p>
      </div>

      {/* Summary Row */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Anomalies (7d)', value: '220', color: 'text-red-400' },
          { label: 'False Positive Rate',  value: '2.6%', color: 'text-amber-400' },
          { label: 'Avg. Detection Time',  value: '4.2 min', color: 'text-ocean-400' },
        ].map(({ label, value, color }) => (
          <div key={label} className="glass-card p-5 text-center">
            <p className="label-text mb-2">{label}</p>
            <p className={`text-3xl font-bold ${color}`}>{value}</p>
          </div>
        ))}
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Weekly Bar Chart */}
        <div className="glass-card p-5">
          <h3 className="section-title mb-4">Weekly Anomaly Count</h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={weeklyAnomalies} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a3a5c40" />
              <XAxis dataKey="day" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...TooltipStyle} />
              <Bar dataKey="count" fill="#00b4d8" radius={[4, 4, 0, 0]} maxBarSize={40} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Hourly Line Chart */}
        <div className="glass-card p-5">
          <h3 className="section-title mb-4">Hourly Detection Rate</h3>
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={anomalyTrend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1a3a5c40" />
              <XAxis dataKey="time" tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: '#64748b', fontSize: 11 }} axisLine={false} tickLine={false} />
              <Tooltip {...TooltipStyle} />
              <Legend wrapperStyle={{ fontSize: 11, color: '#64748b' }} />
              <Line type="monotone" dataKey="spoofing"     stroke="#ef4444" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="darkShip"     stroke="#00b4d8" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="speedAnomaly" stroke="#f59e0b" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="unauthorized" stroke="#a855f7" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Zone Risk Radar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-card p-5">
          <h3 className="section-title mb-4">Zone Risk Assessment</h3>
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={zoneRiskData}>
              <PolarGrid stroke="#1a3a5c" />
              <PolarAngleAxis dataKey="zone" tick={{ fill: '#64748b', fontSize: 11 }} />
              <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 10 }} />
              <Radar name="Risk Score" dataKey="risk" stroke="#00b4d8" fill="#00b4d8" fillOpacity={0.2} strokeWidth={2} />
              <Tooltip {...TooltipStyle} formatter={v => [`${v}`, 'Risk Score']} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* AI Model Stats */}
        <div className="glass-card p-5 space-y-4">
          <h3 className="section-title">AI Model Performance</h3>
          {[
            { metric: 'Precision',    value: 97.4, color: '#00b4d8' },
            { metric: 'Recall',       value: 94.1, color: '#10b981' },
            { metric: 'F1 Score',     value: 95.7, color: '#f59e0b' },
            { metric: 'AUC-ROC',      value: 98.2, color: '#a855f7' },
            { metric: 'Specificity',  value: 99.1, color: '#48cae4' },
          ].map(({ metric, value, color }) => (
            <div key={metric}>
              <div className="flex justify-between text-sm mb-1.5">
                <span className="text-slate-400">{metric}</span>
                <span className="font-semibold" style={{ color }}>{value}%</span>
              </div>
              <div className="h-1.5 bg-navy-700 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${value}%`, background: color }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
