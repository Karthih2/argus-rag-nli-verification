/** Small SVG charts drawn from API data (no chart library needed). Width is responsive via viewBox. */
import { DECISION_COLOR, DECISION_ORDER, DECISIONS } from '../../lib/verdicts'

const W = 600
const H = 240
const PAD = { l: 40, r: 12, t: 12, b: 34 }
const AXIS = '#2A2827'
const LABEL = '#8A867A'

function niceMax(v) {
  if (v <= 4) return 4
  const step = 10 ** Math.floor(Math.log10(v))
  return Math.ceil(v / step) * step
}

function YGrid({ max, fmt = (v) => v }) {
  const ticks = [0, max / 2, max]
  const y = (v) => H - PAD.b - ((H - PAD.t - PAD.b) * v) / max
  return ticks.map((t) => (
    <g key={t}>
      <path d={`M${PAD.l} ${y(t)}H${W - PAD.r}`} stroke={AXIS} />
      <text x={PAD.l - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill={LABEL}>{fmt(t)}</text>
    </g>
  ))
}

export function Legend({ items }) {
  return (
    <ul className="m-0 flex list-none flex-wrap gap-4 p-0 text-[13px] text-soft">
      {items.map(([label, color]) => (
        <li key={label} className="flex items-center gap-2"><span className="h-[11px] w-[11px] rounded-[3px]" style={{ background: color }} />{label}</li>
      ))}
    </ul>
  )
}

export function DecisionLegend() {
  return <Legend items={DECISION_ORDER.map((d) => [DECISIONS[d].label, DECISION_COLOR[d]])} />
}

/** Stacked bars of decisions per day. data: [{day, ACCEPT, ...}] */
export function DecisionBars({ data }) {
  const totals = data.map((d) => DECISION_ORDER.reduce((s, k) => s + (d[k] || 0), 0))
  const max = niceMax(Math.max(1, ...totals))
  const step = (W - PAD.l - PAD.r) / data.length
  const bw = Math.min(28, step * 0.62)
  const ph = (H - PAD.t - PAD.b) / max
  const every = Math.ceil(data.length / 7)
  return (
    <svg role="img" aria-label={`Decisions per day over ${data.length} days`} viewBox={`0 0 ${W} ${H}`} className="w-full font-sans">
      <YGrid max={max} />
      {data.map((d, i) => {
        let y = H - PAD.b
        const x = PAD.l + i * step + (step - bw) / 2
        return (
          <g key={d.day}>
            <title>{`${d.day}: ${totals[i]} questions`}</title>
            {DECISION_ORDER.map((k) => {
              const h = (d[k] || 0) * ph
              if (!h) return null
              y -= h
              return <rect key={k} x={x} y={y} width={bw} height={Math.max(h - 1, 1)} rx="2" fill={DECISION_COLOR[k]} />
            })}
            {i % every === 0 && <text x={x + bw / 2} y={H - 12} textAnchor="middle" fontSize="11" fill={LABEL}>{d.day.slice(5)}</text>}
          </g>
        )
      })}
    </svg>
  )
}

/** Histogram of trust scores in bins of 10. */
export function TrustHistogram({ bins }) {
  const max = niceMax(Math.max(1, ...bins))
  const step = (W - PAD.l - PAD.r) / bins.length
  const ph = (H - PAD.t - PAD.b) / max
  const color = (i) => (i >= 8 ? '#8DB87A' : i >= 6 ? '#C9973A' : '#57534C')
  return (
    <svg role="img" aria-label="Trust score histogram" viewBox={`0 0 ${W} ${H}`} className="w-full font-sans">
      <YGrid max={max} />
      {bins.map((n, i) => (
        <g key={i}>
          <title>{`${i * 10}–${i * 10 + 9}: ${n}`}</title>
          <rect x={PAD.l + i * step + 3} y={H - PAD.b - n * ph} width={step - 6} height={n * ph} rx="2" fill={color(i)} />
        </g>
      ))}
      {[0, 2, 4, 6, 8, 10].map((i) => (
        <text key={i} x={PAD.l + i * step} y={H - 12} textAnchor="middle" fontSize="11" fill={LABEL}>{i * 10}</text>
      ))}
    </svg>
  )
}

/** Median and 95th percentile latency per day (seconds), with an 8 s target line. */
export function LatencyLines({ series, targetMs = 8000 }) {
  const vals = series.flatMap((s) => [s.p50, s.p95]).filter((v) => v != null)
  const max = niceMax(Math.max(targetMs, ...vals) / 1000)
  const step = (W - PAD.l - PAD.r) / Math.max(1, series.length - 1)
  const y = (ms) => H - PAD.b - ((H - PAD.t - PAD.b) * ms) / 1000 / max
  const path = (key) => {
    let d = ''
    series.forEach((s, i) => {
      if (s[key] == null) return
      d += `${d ? 'L' : 'M'}${PAD.l + i * step} ${y(s[key])}`
    })
    return d
  }
  const every = Math.ceil(series.length / 7)
  return (
    <svg role="img" aria-label="Time to answer per day, median and 95th percentile" viewBox={`0 0 ${W} ${H}`} className="w-full font-sans">
      <YGrid max={max} fmt={(v) => `${v}s`} />
      <path d={`M${PAD.l} ${y(targetMs)}H${W - PAD.r}`} stroke="#810100" strokeDasharray="5 4" />
      <text x={W - PAD.r - 2} y={y(targetMs) - 6} textAnchor="end" fontSize="11" fill="#C9C5B6">8 s target</text>
      <path d={path('p95')} fill="none" stroke="#A8A496" strokeWidth="2" />
      <path d={path('p50')} fill="none" stroke="#EDEBDD" strokeWidth="2.5" />
      {series.map((s, i) => i % every === 0 && <text key={s.day} x={PAD.l + i * step} y={H - 12} textAnchor="middle" fontSize="11" fill={LABEL}>{s.day.slice(5)}</text>)}
    </svg>
  )
}

/** Reliability diagram: predicted trust vs observed accuracy, with the diagonal. */
export function Reliability({ points }) {
  const S = 240
  const ox = 44
  const oy = 256
  const P = (v) => [ox + v.predicted * S, oy - v.observed * S]
  return (
    <svg role="img" aria-label="Reliability diagram" viewBox="0 0 320 300" className="w-full max-w-[340px] font-sans">
      {[0.25, 0.5, 0.75, 1].map((k) => <path key={k} d={`M${ox} ${oy - k * S}H${ox + S}M${ox + k * S} ${oy}V${oy - S}`} stroke={AXIS} />)}
      <path d={`M${ox} ${oy}V${oy - S}M${ox} ${oy}H${ox + S}`} stroke="#3A3734" />
      <path d={`M${ox} ${oy}L${ox + S} ${oy - S}`} stroke="#57534C" strokeDasharray="4 5" />
      {points.length > 1 && <polyline points={points.map((p) => P(p).join(',')).join(' ')} fill="none" stroke="#EDEBDD" strokeWidth="2" />}
      {points.map((p) => {
        const [x, yy] = P(p)
        return <circle key={p.predicted} cx={x} cy={yy} r={4 + Math.min(4, p.n / 10)} fill="#181717" stroke="#EDEBDD" strokeWidth="2"><title>{`predicted ${p.predicted}, observed ${p.observed}, n=${p.n}`}</title></circle>
      })}
      {[0, 0.5, 1].map((k) => (
        <g key={k}>
          <text x={ox + k * S} y={oy + 18} textAnchor="middle" fontSize="11" fill={LABEL}>{k}</text>
          <text x={ox - 8} y={oy - k * S + 4} textAnchor="end" fontSize="11" fill={LABEL}>{k}</text>
        </g>
      ))}
      <text x={ox + S / 2} y={296} textAnchor="middle" fontSize="11" fill="#A8A496">Predicted trust</text>
    </svg>
  )
}
