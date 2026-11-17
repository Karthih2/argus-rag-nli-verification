/** Health-based status shown live in the dock. */
import { createContext, useContext, useMemo, useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/hooks'

const ActivityContext = createContext(null)

export function ActivityProvider({ children }) {
  const [answering, setAnswering] = useState(null)
  const [lastDone, setLastDone] = useState(null)
  const health = useApi(() => api.health(), [], { poll: 30000 })

  const value = useMemo(() => {
    const ok = health.data?.status === 'ok'
    const idle = health.data
      ? { title: ok ? 'Ready' : 'Database or search index not ready', meta: ok ? 'Atlas, Groq connected' : 'check /api/health', progress: 1, tone: ok ? 'ok' : 'warn' }
      : { title: 'Connecting', meta: '', progress: 0.2, tone: 'busy' }
    return { live: answering || lastDone || idle, setAnswering, setLastDone, health: health.data }
  }, [health.data, answering, lastDone])

  return <ActivityContext.Provider value={value}>{children}</ActivityContext.Provider>
}

export const useActivity = () => useContext(ActivityContext)
