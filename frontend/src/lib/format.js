/** Formatting helpers for numbers, times and dates. */

export const seconds = (ms) => (ms == null ? '—' : `${(ms / 1000).toFixed(1)} s`)
export const pct = (n, total) => (total ? `${Math.round((100 * n) / total)}%` : '—')
/** 0.047 -> '4.7%' */
export const share = (x, digits = 1) => (x == null ? '—' : `${(x * 100).toFixed(digits)}%`)
export const fixed = (x, digits = 2) => (x == null ? '—' : Number(x).toFixed(digits))
export const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`

export function shortDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

export function timeAgo(iso) {
  if (!iso) return ''
  const s = (Date.now() - new Date(iso).getTime()) / 1000
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)} min ago`
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`
  return shortDate(iso)
}
