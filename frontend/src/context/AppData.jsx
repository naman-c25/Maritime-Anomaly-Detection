import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { api } from '../api'

const AppDataContext = createContext(null)
const POLL_MS = 5000

export function AppDataProvider({ children }) {
  const [state, setState] = useState(null)
  const [online, setOnline] = useState(null)      // null = not checked yet
  const [error, setError] = useState(null)
  const timer = useRef(null)

  const refresh = useCallback(async () => {
    try {
      const s = await api.state()
      // keep the same object when nothing changed, so charts do not re-animate on every poll
      setState(prev => (prev && prev.updated_at === s.updated_at &&
                        JSON.stringify(prev.jobs) === JSON.stringify(s.jobs) ? prev : s))
      setOnline(true)
      setError(null)
      return s
    } catch (e) {
      setOnline(false)
      setError(e.message)
      return null
    }
  }, [])

  useEffect(() => {
    refresh()
    timer.current = setInterval(refresh, POLL_MS)
    return () => clearInterval(timer.current)
  }, [refresh])

  // Polls a background job until it finishes; onProgress receives the job object.
  const waitForJob = useCallback(async (jobId, onProgress) => {
    for (;;) {
      const job = await api.job(jobId)
      onProgress?.(job)
      if (job.status === 'done') { await refresh(); return job }
      if (job.status === 'error') throw new Error(job.error || 'processing failed')
      await new Promise(r => setTimeout(r, 1000))
    }
  }, [refresh])

  const actions = {
    refresh,
    waitForJob,
    loadDemo: async () => {
      const r = await api.loadDemo()
      setState(r.state)
      return r.job
    },
    uploadAis: async file => setState(await api.uploadAis(file)),
    uploadVision: (file, camera, start) => api.uploadVision(file, camera, start),
    saveSettings: async body => setState(await api.saveSettings(body)),
    setAlertStatus: async (id, status) => {
      await api.setAlert(id, status)
      setState(s => s && { ...s, alerts: s.alerts.map(a => (a.id === id ? { ...a, status } : a)) })
    },
  }

  return (
    <AppDataContext.Provider value={{ state, online, error, ...actions }}>
      {children}
    </AppDataContext.Provider>
  )
}

export const useAppData = () => useContext(AppDataContext)
