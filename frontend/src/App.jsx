import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout/Layout'
import { AppDataProvider } from './context/AppData'
import LiveAnalysis from './pages/LiveAnalysis'
import Dashboard from './pages/Dashboard'
import VesselTracking from './pages/VesselTracking'
import AnomalyAlerts from './pages/AnomalyAlerts'
import Analytics from './pages/Analytics'
import Settings from './pages/Settings'

export default function App() {
  return (
    <AppDataProvider>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard"      element={<Dashboard />} />
          <Route path="live-analysis"   element={<LiveAnalysis />} />
          <Route path="vessel-tracking" element={<VesselTracking />} />
          <Route path="anomaly-alerts"  element={<AnomalyAlerts />} />
          <Route path="analytics"       element={<Analytics />} />
          <Route path="settings"        element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </AppDataProvider>
  )
}
