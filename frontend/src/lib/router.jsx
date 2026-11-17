/** Tiny history router for Argus. */
import { useEffect, useState } from 'react'

const ROUTES = [
  ['landing', /^\/$/],
  ['upload', /^\/upload\/?$/],
  ['processing', /^\/processing\/([^/]+)\/?$/],
  ['dashboard', /^\/dashboard\/([^/]+)\/?$/],
  ['analytics', /^\/analytics\/?$/],
]
const PARAM_NAMES = { processing: ['id'], dashboard: ['sessionId'] }

export function matchRoute(pathname) {
  for (const [name, re] of ROUTES) {
    const m = pathname.match(re)
    if (m) return { name, params: Object.fromEntries((PARAM_NAMES[name] || []).map((k, i) => [k, decodeURIComponent(m[i + 1])])) }
  }
  return { name: 'notFound', params: {} }
}

export function navigate(to, { replace = false } = {}) {
  window.history[replace ? 'replaceState' : 'pushState']({}, '', to)
  window.dispatchEvent(new PopStateEvent('popstate'))
  window.scrollTo({ top: 0 })
}

export function useLocation() {
  const [loc, setLoc] = useState(() => ({ pathname: window.location.pathname, search: window.location.search, hash: window.location.hash }))
  useEffect(() => {
    const update = () => setLoc({ pathname: window.location.pathname, search: window.location.search, hash: window.location.hash })
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [])
  return loc
}

export function Link({ to, onClick, ...props }) {
  function handle(e) {
    onClick?.(e)
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return
    if (to.startsWith('#')) return
    e.preventDefault()
    navigate(to)
  }
  return <a href={to} onClick={handle} {...props} />
}
