/** Data hooks: load from the API, optionally poll, and reload on demand. */
import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * useApi(() => api.x(...), [deps], { poll: ms, enabled })
 * Returns { data, error, loading, reload }. Keeps the previous data while reloading, so lists don't flash.
 */
export function useApi(fetcher, deps = [], { poll = 0, enabled = true } = {}) {
  const [state, setState] = useState({ data: undefined, error: null, loading: enabled })
  const fetchRef = useRef(fetcher)
  fetchRef.current = fetcher

  const reload = useCallback(async () => {
    try {
      const data = await fetchRef.current()
      setState({ data, error: null, loading: false })
    } catch (error) {
      setState((s) => ({ ...s, error, loading: false }))
    }
  }, [])

  useEffect(() => {
    if (!enabled) return undefined
    setState((s) => ({ ...s, loading: true }))
    reload()
    if (!poll) return undefined
    const id = setInterval(reload, poll)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, poll, enabled, reload])

  return { ...state, reload }
}
