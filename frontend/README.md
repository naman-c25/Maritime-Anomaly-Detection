# Part 1: Frontend (website)

React + Vite + Tailwind dashboard. It gets all its data from the fusion API (`/api/...`).

| Page | File | Shows |
|---|---|---|
| Dashboard | `src/pages/Dashboard.jsx` | KPIs, AIS anomaly score over time, alerts by type, latest alerts |
| Live Analysis | `src/pages/LiveAnalysis.jsx` | upload AIS CSV / video / image, annotated video, results |
| Vessel Tracking | `src/pages/VesselTracking.jsx` | map: AIS tracks, camera, restricted zone, camera tracks |
| Anomaly Alerts | `src/pages/AnomalyAlerts.jsx` | fused alerts with evidence, status, CSV export |
| Analytics | `src/pages/Analytics.jsx` | error per vessel, error distribution, model details, detector test results |
| Settings | `src/pages/Settings.jsx` | fusion α, alert levels, matching distance / time |

`src/api.js` calls the API, and `src/context/AppData.jsx` keeps the shared data (refreshed every 5 s).

```
npm install
npm run dev      # http://localhost:5173 (needs the API on port 8000)
npm run build    # creates dist/, served by the API at http://localhost:8000
```
