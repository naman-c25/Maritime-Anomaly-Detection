// ── Mock data for the Maritime Guard dashboard ──────────────

export const kpiData = [
  {
    id: 'active-vessels',
    label: 'Active Vessels',
    value: '1,247',
    delta: '+12 today',
    deltaUp: true,
    icon: 'Ship',
    color: 'ocean',
  },
  {
    id: 'anomalies-detected',
    label: 'Anomalies Detected',
    value: '38',
    delta: '+5 this hour',
    deltaUp: false,
    icon: 'AlertTriangle',
    color: 'red',
  },
  {
    id: 'zones-monitored',
    label: 'Zones Monitored',
    value: '24',
    delta: 'All operational',
    deltaUp: true,
    icon: 'MapPin',
    color: 'green',
  },
  {
    id: 'ai-model-accuracy',
    label: 'AI Model Accuracy',
    value: '97.4%',
    delta: '+0.3% vs last week',
    deltaUp: true,
    icon: 'Cpu',
    color: 'amber',
  },
]

export const recentAlerts = [
  { id: 'ALT-001', vessel: 'MV Pacific Star',   mmsi: '366998410', type: 'AIS Spoofing',        severity: 'critical', zone: 'Strait of Malacca', time: '04:12 UTC', status: 'Active' },
  { id: 'ALT-002', vessel: 'KM Nusantara',       mmsi: '525019234', type: 'Dark Ship Activity',  severity: 'high',     zone: 'Arabian Sea',       time: '03:58 UTC', status: 'Active' },
  { id: 'ALT-003', vessel: 'MV Sea Wanderer',    mmsi: '636014876', type: 'Speed Anomaly',       severity: 'medium',   zone: 'Bay of Bengal',     time: '03:44 UTC', status: 'Reviewing' },
  { id: 'ALT-004', vessel: 'SS Iron Titan',      mmsi: '477039812', type: 'Unauthorized Zone',   severity: 'high',     zone: 'Exclusive EEZ',     time: '03:31 UTC', status: 'Active' },
  { id: 'ALT-005', vessel: 'MV Orion Voyager',   mmsi: '229183000', type: 'Route Deviation',     severity: 'low',      zone: 'Red Sea',           time: '03:15 UTC', status: 'Resolved' },
  { id: 'ALT-006', vessel: 'Bulk Carrier Alpha',  mmsi: '538007812', type: 'Loitering',           severity: 'medium',   zone: 'Gulf of Aden',      time: '02:58 UTC', status: 'Reviewing' },
]

export const anomalyTrend = [
  { time: '00:00', spoofing: 2, darkShip: 1, speedAnomaly: 3, unauthorized: 1 },
  { time: '01:00', spoofing: 1, darkShip: 2, speedAnomaly: 2, unauthorized: 2 },
  { time: '02:00', spoofing: 3, darkShip: 1, speedAnomaly: 4, unauthorized: 1 },
  { time: '03:00', spoofing: 5, darkShip: 3, speedAnomaly: 2, unauthorized: 3 },
  { time: '04:00', spoofing: 4, darkShip: 2, speedAnomaly: 5, unauthorized: 2 },
  { time: '05:00', spoofing: 6, darkShip: 4, speedAnomaly: 3, unauthorized: 4 },
  { time: '06:00', spoofing: 3, darkShip: 3, speedAnomaly: 6, unauthorized: 2 },
  { time: '07:00', spoofing: 7, darkShip: 5, speedAnomaly: 4, unauthorized: 5 },
  { time: '08:00', spoofing: 4, darkShip: 2, speedAnomaly: 7, unauthorized: 3 },
]

export const vesselsByType = [
  { name: 'Cargo',      value: 487, color: '#00b4d8' },
  { name: 'Tanker',     value: 312, color: '#0096c7' },
  { name: 'Container',  value: 248, color: '#48cae4' },
  { name: 'Fishing',    value: 134, color: '#0077b6' },
  { name: 'Passenger',  value: 66,  color: '#90e0ef' },
]

export const vessels = [
  { id: 'V001', name: 'MV Pacific Star',    mmsi: '366998410', type: 'Cargo',     flag: 'US', lat: 1.35,   lng: 104.0,  speed: 12.4, heading: 145, status: 'anomaly',  lastSeen: '2m ago' },
  { id: 'V002', name: 'KM Nusantara',       mmsi: '525019234', type: 'Tanker',    flag: 'ID', lat: 5.55,   lng: 95.3,   speed: 0.2,  heading: 0,   status: 'dark',     lastSeen: '18m ago' },
  { id: 'V003', name: 'MV Sea Wanderer',    mmsi: '636014876', type: 'Container', flag: 'LR', lat: 13.0,   lng: 80.2,   speed: 22.1, heading: 210, status: 'anomaly',  lastSeen: '5m ago' },
  { id: 'V004', name: 'SS Iron Titan',      mmsi: '477039812', type: 'Bulk',      flag: 'HK', lat: 20.5,   lng: 88.5,   speed: 8.7,  heading: 320, status: 'normal',   lastSeen: '1m ago' },
  { id: 'V005', name: 'MV Orion Voyager',   mmsi: '229183000', type: 'Cargo',     flag: 'GR', lat: 15.5,   lng: 42.5,   speed: 14.2, heading: 55,  status: 'normal',   lastSeen: '3m ago' },
  { id: 'V006', name: 'Bulk Carrier Alpha', mmsi: '538007812', type: 'Bulk',      flag: 'MH', lat: 11.8,   lng: 44.0,   speed: 3.1,  heading: 180, status: 'anomaly',  lastSeen: '8m ago' },
  { id: 'V007', name: 'MT Gulf Pioneer',    mmsi: '403001234', type: 'Tanker',    flag: 'SA', lat: 25.0,   lng: 56.0,   speed: 11.8, heading: 90,  status: 'normal',   lastSeen: '4m ago' },
  { id: 'V008', name: 'MV Aurora Express',  mmsi: '319087000', type: 'Container', flag: 'KY', lat: 3.1,    lng: 98.7,   speed: 18.3, heading: 135, status: 'normal',   lastSeen: '2m ago' },
]

export const weeklyAnomalies = [
  { day: 'Mon', count: 22 },
  { day: 'Tue', count: 31 },
  { day: 'Wed', count: 19 },
  { day: 'Thu', count: 45 },
  { day: 'Fri', count: 38 },
  { day: 'Sat', count: 27 },
  { day: 'Sun', count: 38 },
]

export const zoneRiskData = [
  { zone: 'Malacca',  risk: 87 },
  { zone: 'Arabian Sea', risk: 72 },
  { zone: 'Gulf Aden', risk: 91 },
  { zone: 'Bay Bengal', risk: 45 },
  { zone: 'Red Sea',  risk: 68 },
  { zone: 'Indian Ocean', risk: 33 },
]

// Full alerts list — recentAlerts + additional entries for the Anomaly Alerts page
// NOTE: All data is static mock data. No backend connection exists.
export const allAlerts = [
  ...recentAlerts,
  { id: 'ALT-007', vessel: 'MT Gulf Pioneer',    mmsi: '403001234', type: 'Course Deviation',   severity: 'low',    zone: 'Persian Gulf',   time: '02:40 UTC', status: 'Resolved' },
  { id: 'ALT-008', vessel: 'MV Aurora Express',  mmsi: '319087000', type: 'AIS Gap',            severity: 'medium', zone: 'Malacca Strait', time: '02:25 UTC', status: 'Reviewing' },
  { id: 'ALT-009', vessel: 'FV Deep Sea Fisher', mmsi: '567891234', type: 'Dark Ship Activity', severity: 'high',   zone: 'Bay of Bengal',  time: '01:55 UTC', status: 'Active' },
  { id: 'ALT-010', vessel: 'MV Coral Princess',  mmsi: '215678901', type: 'Speed Anomaly',      severity: 'medium', zone: 'Red Sea',        time: '01:30 UTC', status: 'Resolved' },
]
