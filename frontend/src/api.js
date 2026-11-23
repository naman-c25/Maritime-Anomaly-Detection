// Backend base URL. Empty = same origin (the backend serves the built frontend, and `npm run dev` proxies /api).
// For a separately hosted frontend (e.g. Vercel) set VITE_API_URL=https://<your-backend>.
export const API_URL = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export const mediaUrl = path => (path ? `${API_URL}${path}` : null)

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, options)
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail ?? detail } catch { /* not JSON */ }
    throw new Error(typeof detail === 'string' ? detail : JSON.stringify(detail))
  }
  return res.json()
}

const json = (method, body) => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

const upload = (file, extra = {}) => {
  const form = new FormData()
  form.append('file', file)
  Object.entries(extra).forEach(([k, v]) => v != null && v !== '' && form.append(k, v))
  return { method: 'POST', body: form }
}

export const api = {
  health:        ()                      => request('/api/health'),
  state:         ()                      => request('/api/state'),
  loadDemo:      ()                      => request('/api/demo/load', { method: 'POST' }),
  rebuildDemo:   ()                      => request('/api/demo/rebuild', { method: 'POST' }),
  uploadAis:     file                    => request('/api/ais/upload', upload(file)),
  uploadVision:  (file, camera, start)   => request('/api/vision/upload', upload(file, { camera, start_time: start })),
  job:           id                      => request(`/api/jobs/${id}`),
  saveSettings:  body                    => request('/api/settings', json('PUT', body)),
  setAlert:      (id, status)            => request(`/api/alerts/${encodeURIComponent(id)}`, json('PATCH', { status })),
  demoCsvUrl:    `${API_URL}/api/demo/ais.csv`,
}
