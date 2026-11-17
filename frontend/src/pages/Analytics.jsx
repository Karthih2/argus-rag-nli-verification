/** Analytics: how answers were decided, trust distribution, and how fast it runs. */
import { useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/hooks'
import { DecisionBars, DecisionLegend, Legend, LatencyLines, TrustHistogram } from '../components/charts'
import { PageState, TopBar } from '../components/TopBar'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Display, Skeleton } from '../components/ui/misc'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import { Tabs } from '../components/ui/tabs'
import { DecisionBadge } from '../features/answer'
import { pickDemo } from '../lib/chat'
import { pct, seconds, timeAgo } from '../lib/format'
import { navigate } from '../lib/router'
import { cn } from '../lib/utils'

const RANGES = [7, 14, 30, 90]
const PAGE = 10
const STAGE_COLOR = { retrieve: '#57534C', rerank: '#A8A496', llm: '#EDEBDD', verify: '#8DB87A' }

function StatStrip({ t }) {
  const d = t.decisions
  const cells = [
    ['Questions', t.questions, 'in this period'],
    ['Verified', pct(d.ACCEPT, t.questions), `${d.ACCEPT} answers`],
    ['Partly or warned', pct(d.ACCEPT_LOW_CONFIDENCE + d.WARN, t.questions), `${d.ACCEPT_LOW_CONFIDENCE + d.WARN} answers`],
    ['Withheld', pct(d.BLOCK, t.questions), `${d.BLOCK} answers`],
    ['Average trust', t.avg_trust ?? '—', 'out of 100'],
    ['Median time', seconds(t.p50_ms), `95th: ${seconds(t.p95_ms)}`],
  ]
  return (
    <dl className="m-0 grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-px overflow-hidden rounded-[14px] border border-border bg-border">
      {cells.map(([k, v, note]) => (
        <div key={k} className="bg-card px-6 py-5">
          <dt className="text-[13px] text-muted">{k}</dt>
          <dd className="m-0 mt-1.5 text-3xl font-semibold tabular">{v}</dd>
          <dd className="m-0 mt-1 text-[13px] text-faint">{note}</dd>
        </div>
      ))}
    </dl>
  )
}

function ChartCard({ title, description, children, className }) {
  return (
    <Card className={cn('anim-rise', className)}>
      <CardHeader><CardTitle>{title}</CardTitle><CardDescription>{description}</CardDescription></CardHeader>
      <CardContent className="flex flex-col gap-4">{children}</CardContent>
    </Card>
  )
}

const Empty = ({ children }) => <p className="m-0 py-10 text-center text-sm text-muted">{children}</p>

function QueryLog({ datasetId }) {
  const [page, setPage] = useState(0)
  const { data, loading } = useApi(() => api.queries({ datasetId, limit: PAGE, skip: page * PAGE }), [datasetId, page])
  return (
    <ChartCard title="Recent questions" description="Newest first. Open one to see its answer and evidence." className="col-span-full">
      {loading && !data ? <Skeleton className="h-48 w-full" /> : !data?.items.length ? <Empty>No questions asked yet.</Empty> : (
        <>
          <div className="-mx-6">
            <Table className="min-w-[640px]">
              <TableHeader><TableRow><TableHead className="px-6">Question</TableHead><TableHead>Decision</TableHead><TableHead className="text-right">Trust</TableHead><TableHead className="text-right">Time</TableHead><TableHead className="pr-6">Asked</TableHead></TableRow></TableHeader>
              <TableBody>
                {data.items.map((q) => (
                  <TableRow key={q._id} onClick={() => q.session_id && navigate(`/chat/${q.session_id}`)} className={cn(q.session_id && 'cursor-pointer hover:bg-[#232121]')}>
                    <TableCell className="px-6">{q.question}</TableCell>
                    <TableCell><DecisionBadge decision={q.decision} /></TableCell>
                    <TableCell className="text-right tabular">{q.decision === 'NO_SUPPORT' ? '—' : q.trust}</TableCell>
                    <TableCell className="text-right text-muted tabular">{seconds(q.latency_ms?.total)}</TableCell>
                    <TableCell className="pr-6 text-muted">{timeAgo(q.ts)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <nav aria-label="Pages" className="flex items-center justify-between text-sm text-muted">
            <span>{page * PAGE + 1}–{page * PAGE + data.items.length} of {data.total}</span>
            <span className="flex gap-2">
              <Button variant="secondary" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>Previous</Button>
              <Button variant="secondary" size="sm" disabled={(page + 1) * PAGE >= data.total} onClick={() => setPage((p) => p + 1)}>Next</Button>
            </span>
          </nav>
        </>
      )}
    </ChartCard>
  )
}

function TrustModelCard() {
  const { data: info } = useApi(() => api.trustInfo(), [])
  if (!info || !info.fitted) return null
  const m = info.metrics ?? {}
  const th = info.thresholds ?? {}
  const rows = [
    ['Temperature', info.temperature?.toFixed(4)],
    ['Verified threshold', th.verified != null ? `≥ ${th.verified}` : '—'],
    ['Withheld threshold', th.withheld != null ? `≤ ${th.withheld}` : 'none'],
    ['AUROC', m.auroc?.toFixed(4)],
    ['Brier score', m.brier?.toFixed(4)],
    ['ECE', m.ece?.toFixed(4)],
    ['Verified error (observed)', m.verified_observed_error != null ? pct(m.verified_observed_error * m.test_n, m.test_n) : '—'],
    ['Verified error (target)', m.verified_target != null ? `≤ ${(m.verified_target * 100).toFixed(1)}%` : '—'],
  ]
  return (
    <ChartCard title="Trust model" description={`v${info.version} — fitted ${info.fit_date?.slice(0, 10) ?? '?'}`}>
      <Table>
        <TableBody>
          {rows.map(([k, v]) => (
            <TableRow key={k}><TableCell className="text-muted">{k}</TableCell><TableCell className="text-right tabular">{v}</TableCell></TableRow>
          ))}
        </TableBody>
      </Table>
      {info.data_sources && <p className="m-0 text-[13px] text-faint">Sources: {info.data_sources.join(', ')}</p>}
    </ChartCard>
  )
}

export default function Analytics({ search }) {
  const datasets = useApi(() => api.datasets(), [])
  const [picked, setPicked] = useState(() => new URLSearchParams(search).get('dataset'))
  const [days, setDays] = useState(14)
  const datasetId = picked ?? pickDemo(datasets.data)?._id
  const stats = useApi(() => api.analytics(datasetId, days), [datasetId, days], { enabled: Boolean(datasetId) })
  const s = stats.data
  const stageMs = s?.latency.stage_median_ms ?? {}
  const stageTotal = Object.values(stageMs).reduce((a, b) => a + (b || 0), 0)

  return (
    <>
      <TopBar crumbs={[{ label: 'Analytics' }]} />
      <main className="mx-auto flex max-w-[1280px] flex-col gap-6 px-8 pt-11 pb-40">
        <div className="flex flex-wrap items-end justify-between gap-5">
          <div>
            <Display as="h1" className="text-[56px] leading-none">Analytics</Display>
            <p className="mt-2.5 mb-0 text-base text-muted">How answers were decided, trust distribution, and how fast it runs.</p>
          </div>
          <div className="flex flex-wrap items-center gap-3">
            <label className="flex items-center gap-2.5 text-sm text-muted">
              Dataset
              <select value={datasetId ?? ''} onChange={(e) => setPicked(e.target.value)}
                className="h-10 rounded-[10px] border border-line-strong bg-card px-3 text-sm text-cotton">
                {(datasets.data ?? []).map((d) => <option key={d._id} value={d._id}>{d.name}</option>)}
              </select>
            </label>
            <Tabs label="Time range" value={days} onValueChange={setDays} items={RANGES.map((d) => ({ value: d, label: `${d} days` }))} />
          </div>
        </div>
        <PageState loading={(datasets.loading || stats.loading) && !s} error={stats.error || datasets.error}
          empty={datasets.data?.length === 0 && <p className="text-muted">No datasets yet.</p>}>
          {s && (
            <>
              <StatStrip t={s.totals} />
              <div className="grid grid-cols-[repeat(auto-fit,minmax(min(100%,480px),1fr))] gap-6">
                <ChartCard title="Decisions per day" description="Every answer gets one decision. Withheld answers were contradicted by the source.">
                  {s.totals.questions ? <><DecisionBars data={s.per_day} /><DecisionLegend /></> : <Empty>No questions in this period.</Empty>}
                </ChartCard>
                <ChartCard title="Trust scores" description="Probability that an answer is correct, in bins of 10.">
                  {s.trust_histogram.some(Boolean) ? (
                    <><TrustHistogram bins={s.trust_histogram} /><Legend items={[['80 and above', '#8DB87A'], ['60 to 79', '#C9973A'], ['Below 60', '#57534C']]} /></>
                  ) : <Empty>No scored answers in this period.</Empty>}
                </ChartCard>
                <ChartCard title="Time to answer" description="Median and 95th percentile per day, and where the time goes.">
                  {s.latency.series.some((x) => x.p50 != null) ? (
                    <>
                      <LatencyLines series={s.latency.series} />
                      <Legend items={[['Median', '#EDEBDD'], ['95th percentile', '#A8A496']]} />
                      {stageTotal > 0 && (
                        <div className="flex flex-col gap-2.5">
                          <span className="text-[13px] text-muted">Median by stage, {seconds(stageTotal)} in total</span>
                          <div className="flex h-3 gap-0.5 overflow-hidden rounded-full">
                            {Object.entries(stageMs).filter(([, v]) => v).map(([k, v]) => <span key={k} title={`${k} ${v} ms`} style={{ flex: `${v} 1 0`, background: STAGE_COLOR[k] }} />)}
                          </div>
                          <Legend items={Object.entries(stageMs).filter(([, v]) => v).map(([k, v]) => [`${k} ${seconds(v)}`, STAGE_COLOR[k]])} />
                        </div>
                      )}
                    </>
                  ) : <Empty>No timings in this period.</Empty>}
                </ChartCard>
                <TrustModelCard />
                <QueryLog datasetId={datasetId} />
              </div>
            </>
          )}
        </PageState>
      </main>
    </>
  )
}
