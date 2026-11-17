/** Evidence panel: top chunks, passage view with highlighted quote, page image, chart. */
import { useEffect, useState } from 'react'
import { urls } from '../api/client'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/misc'
import { Tabs } from '../components/ui/tabs'
import { fixed } from '../lib/format'
import { cn } from '../lib/utils'

const CHART_COLORS = ['#8DB87A', '#C9973A', '#5B8DEF', '#D96B6B', '#9B7ED8', '#57ADB5', '#E0A060']
const CHART_W = 400
const CHART_H = 220
const CHART_PAD = { l: 50, r: 16, t: 16, b: 40 }
const MAX_CHUNKS = 5

function BarChart({ chart }) {
  const { labels, series } = chart
  const n = labels.length
  const allValues = series.flatMap((s) => s.data)
  const max = Math.max(...allValues, 1)
  const plotW = CHART_W - CHART_PAD.l - CHART_PAD.r
  const plotH = CHART_H - CHART_PAD.t - CHART_PAD.b
  const barW = Math.min(plotW / n / series.length - 2, 32)
  const groupW = barW * series.length + 4
  return (
    <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="w-full">
      {labels.map((label, i) => {
        const gx = CHART_PAD.l + (plotW / n) * i + (plotW / n - groupW) / 2
        return (
          <g key={i}>
            {series.map((s, si) => {
              const h = (s.data[i] / max) * plotH
              return <rect key={si} x={gx + si * (barW + 1)} y={CHART_PAD.t + plotH - h} width={barW} height={h} fill={CHART_COLORS[si % CHART_COLORS.length]} rx="2" />
            })}
            <text x={gx + groupW / 2} y={CHART_H - 6} textAnchor="middle" fontSize="10" fill="#8A867A">{label}</text>
          </g>
        )
      })}
    </svg>
  )
}

function LineChart({ chart }) {
  const { labels, series } = chart
  const n = labels.length
  const allValues = series.flatMap((s) => s.data)
  const max = Math.max(...allValues, 1)
  const plotW = CHART_W - CHART_PAD.l - CHART_PAD.r
  const plotH = CHART_H - CHART_PAD.t - CHART_PAD.b
  const x = (i) => CHART_PAD.l + (plotW / Math.max(n - 1, 1)) * i
  const y = (v) => CHART_PAD.t + plotH - (v / max) * plotH
  return (
    <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="w-full">
      {series.map((s, si) => (
        <polyline key={si} fill="none" stroke={CHART_COLORS[si % CHART_COLORS.length]} strokeWidth="2"
          points={s.data.map((v, i) => `${x(i)},${y(v)}`).join(' ')} />
      ))}
      {labels.map((label, i) => (
        <text key={i} x={x(i)} y={CHART_H - 6} textAnchor="middle" fontSize="10" fill="#8A867A">{label}</text>
      ))}
    </svg>
  )
}

function PieChart({ chart }) {
  const { labels, series } = chart
  const data = series[0]?.data ?? []
  const total = data.reduce((a, b) => a + b, 0) || 1
  const cx = CHART_W / 2
  const cy = CHART_H / 2 - 10
  const r = Math.min(cx, cy) - 20
  let angle = -Math.PI / 2
  return (
    <svg viewBox={`0 0 ${CHART_W} ${CHART_H}`} className="w-full">
      {data.map((v, i) => {
        const sweep = (v / total) * 2 * Math.PI
        const x1 = cx + r * Math.cos(angle)
        const y1 = cy + r * Math.sin(angle)
        const x2 = cx + r * Math.cos(angle + sweep)
        const y2 = cy + r * Math.sin(angle + sweep)
        const large = sweep > Math.PI ? 1 : 0
        const path = `M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} Z`
        const mid = angle + sweep / 2
        const lx = cx + (r + 14) * Math.cos(mid)
        const ly = cy + (r + 14) * Math.sin(mid)
        angle += sweep
        return (
          <g key={i}>
            <path d={path} fill={CHART_COLORS[i % CHART_COLORS.length]} />
            {sweep > 0.3 && <text x={lx} y={ly} textAnchor="middle" fontSize="9" fill="#8A867A">{labels[i]}</text>}
          </g>
        )
      })}
    </svg>
  )
}

function EvidenceChart({ chart, page }) {
  const Chart = chart.type === 'pie' ? PieChart : chart.type === 'line' ? LineChart : BarChart
  return (
    <section className="flex flex-col gap-2">
      <Chart chart={chart} />
      <div className="flex flex-wrap gap-2">
        {chart.series.map((s, i) => (
          <span key={i} className="flex items-center gap-1 text-[11px] text-muted">
            <span className="inline-block h-2 w-2 rounded-full" style={{ background: CHART_COLORS[i % CHART_COLORS.length] }} />
            {s.name}
          </span>
        ))}
      </div>
      <span className="text-[11px] text-faint">From table, p.{page}</span>
    </section>
  )
}

/** Passage text with the claim's quote highlighted. */
function Highlighted({ text, quote }) {
  const at = quote ? text.toLowerCase().indexOf(quote.toLowerCase().slice(0, 60)) : -1
  if (at < 0) return text
  const end = Math.min(text.length, at + quote.length)
  return (
    <>
      {text.slice(0, at)}
      <mark className="rounded-[3px] bg-ok-bg px-0.5 text-ok-ink">{text.slice(at, end)}</mark>
      {text.slice(end)}
    </>
  )
}

function PagePreview({ item }) {
  const [loaded, setLoaded] = useState(false)
  useEffect(() => setLoaded(false), [item.chunk_id])
  if (!item.document_id || !item.page) return <p className="m-0 text-sm text-muted">No page image for this passage.</p>
  return (
    <figure className="m-0 overflow-hidden rounded-[10px] bg-cotton shadow-[0_12px_24px_-12px_rgba(0,0,0,.7)]">
      <figcaption className="flex justify-between px-3 py-2 text-[11px] text-graphite">
        <span className="truncate">{item.file_name}</span><span>p.{item.page}</span>
      </figcaption>
      {!loaded && <Skeleton className="aspect-[3/4] w-full rounded-none bg-rule" />}
      <img
        src={urls.page(item.document_id, item.page, item.chunk_id)}
        alt={`Page ${item.page} of ${item.file_name}`}
        onLoad={() => setLoaded(true)}
        className={cn('block w-full', !loaded && 'hidden')}
      />
    </figure>
  )
}

/** Chunk selector — shows top chunks as numbered cards with relevance score. */
function ChunkList({ evidence, activeRef, onRef }) {
  const top = evidence.slice(0, MAX_CHUNKS)
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[11px] font-medium tracking-wide text-faint uppercase">Top {top.length} chunks</span>
      {top.map((e, i) => (
        <button key={e.ref} type="button" onClick={() => onRef(e.ref)}
          className={cn(
            'flex cursor-pointer items-center gap-3 rounded-[10px] border px-3 py-2.5 text-left transition-colors',
            e.ref === activeRef ? 'border-cotton bg-active' : 'border-line-strong hover:border-muted hover:bg-hover',
          )}>
          <span className={cn('grid h-7 w-7 flex-none place-items-center rounded-md text-xs font-semibold', e.ref === activeRef ? 'bg-cherry text-cotton' : 'bg-hover text-muted')}>
            {i + 1}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex items-center justify-between gap-2">
              <span className="truncate text-[12px] font-medium text-cotton">{e.ref} · p.{e.page}</span>
              <span className="flex-none text-[11px] text-faint tabular">{fixed(e.rerank)}</span>
            </div>
            <span className="block truncate text-[11px] text-muted">{e.type}{e.section ? ` — ${e.section}` : ''}</span>
          </div>
        </button>
      ))}
    </div>
  )
}

/** Right-hand evidence column for the selected answer. */
export function EvidencePanel({ turn, activeRef, onRef }) {
  const [view, setView] = useState('passage')
  const evidence = turn?.evidence ?? []
  const item = evidence.find((e) => e.ref === activeRef) ?? evidence[0]
  const claim = turn?.claims?.find((c) => c.cites?.includes(item?.ref))
  useEffect(() => setView('passage'), [turn?.query_id, turn?._id])

  if (!turn) return <p className="m-0 text-sm text-muted">Ask a question to see the passages behind the answer.</p>
  if (!item) return <p className="m-0 text-sm text-muted">No passages were retrieved.</p>

  const hasChart = Boolean(item?.chart)
  const tabs = [
    { value: 'passage', label: 'Passage' },
    { value: 'page', label: 'Page' },
    ...(hasChart ? [{ value: 'chart', label: 'Chart' }] : []),
  ]
  return (
    <div className="flex flex-col gap-4">
      {/* Top chunks list */}
      <ChunkList evidence={evidence} activeRef={item.ref} onRef={onRef} />

      {/* View tabs */}
      <Tabs label="Evidence views" value={view} onValueChange={setView} items={tabs} className="self-start" />

      {/* Content area */}
      {view === 'passage' && (
        <section className="flex flex-col gap-3">
          <div className="flex flex-wrap items-center gap-2 text-[11px] text-muted">
            <Badge>{item.type}</Badge>
            {item.section && <Badge className="max-w-full truncate">{item.section}</Badge>}
            <span className="ml-auto tabular">relevance {fixed(item.rerank)}</span>
          </div>
          <blockquote className="m-0 rounded-[10px] bg-cotton px-4 py-3 font-display text-base leading-normal text-noir">
            <span className="mb-1 block font-sans text-[11px] text-graphite">{item.file_name}, p.{item.page}</span>
            <Highlighted text={item.text} quote={claim?.quote} />
          </blockquote>
        </section>
      )}
      {view === 'page' && <PagePreview item={item} />}
      {view === 'chart' && hasChart && <EvidenceChart chart={item.chart} page={item.page} />}
    </div>
  )
}
