/** Analytics: essential metrics only — decisions, trust, latency. */
import { useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/hooks'
import { DecisionBars, DecisionLegend, Legend, LatencyLines, TrustHistogram } from '../components/charts'
import { Icon } from '../components/icon'
import { HelpButton } from '../components/Navbar'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Display, Skeleton } from '../components/ui/misc'
import { DecisionBadge } from '../features/answer'
import { pickDemo } from '../lib/chat'
import { pct, seconds } from '../lib/format'
import { cn } from '../lib/utils'
import { TRUST_BANDS } from '../lib/verdicts'

function StatCard({ label, value, sub, helpText }) {
  return (
    <div className="relative bg-card px-6 py-6">
      <div className="flex items-start justify-between">
        <dt className="text-sm text-muted">{label}</dt>
        {helpText && <HelpButton topic={helpText} />}
      </div>
      <dd className="m-0 mt-2 text-4xl font-semibold tabular">{value}</dd>
      {sub && <dd className="m-0 mt-1.5 text-sm text-faint">{sub}</dd>}
    </div>
  )
}

function ChartCard({ title, description, helpText, children, className }) {
  return (
    <Card className={cn('anim-rise', className)}>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div>
            <CardTitle className="text-xl">{title}</CardTitle>
            <CardDescription className="text-sm">{description}</CardDescription>
          </div>
          {helpText && <HelpButton topic={helpText} />}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">{children}</CardContent>
    </Card>
  )
}

const Empty = ({ children }) => <p className="m-0 py-10 text-center text-base text-muted">{children}</p>
const STAGE_COLOR = { retrieve: '#57534C', rerank: '#A8A496', llm: '#EDEBDD', verify: '#8DB87A' }
const THRESHOLD_NAMES = { tau_accept: 'Supported at entailment ≥', tau_low: 'Weakly supported at ≥', tau_block: 'Contradicted at contradiction ≥' }
const num = (v, d = 2) => (v == null ? '—' : Number(v).toFixed(d))

/** What the verifier is calibrated with: thresholds (fitted or fallback) and trust-model test metrics. */
function CalibrationCard({ info }) {
  if (!info) return null
  const m = info.metrics ?? {}
  return (
    <ChartCard title="Calibration" className="col-span-full"
      description={info.fitted ? `Version ${info.version} · fitted ${String(info.fit_date ?? '').slice(0, 10)} · NLI temperature ${num(info.temperature)}` : 'Not fitted yet: run python -m scripts.fit_trust'}
      helpText="Claim thresholds are fitted on held-out RAGTruth claims so that, with 95% confidence, at most the stated share of supported claims is wrong. A threshold whose target could not be met uses the fallback value and is marked so. The trust model is tested on contexts it never saw.">
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <table className="w-full border-collapse text-sm">
          <tbody>
            {Object.entries(THRESHOLD_NAMES).map(([key, label]) => (
              <tr key={key} className="border-t border-hover first:border-t-0">
                <td className="py-2 pr-3 text-muted">{label}</td>
                <td className="py-2 pr-3 text-right font-mono tabular">{num(info.thresholds?.[key])}</td>
                <td className="py-2 text-right text-xs">
                  {info.fallback?.includes(key)
                    ? <span className="text-warn">fallback</span>
                    : <span className="text-ok">fitted · bound {num(info.threshold_report?.[key]?.bound, 3)}</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <dl className="m-0 grid grid-cols-3 gap-px overflow-hidden rounded-[var(--radius-md)] border border-border bg-border text-sm">
          {[['AUROC', num(m.auroc)], ['Brier', num(m.brier, 3)], ['ECE', num(m.ece, 3)],
            ['Risk target', info.risk ? `${Math.round(info.risk.verified * 100)}%` : '—'],
            ['Claim error (test)', m.claim_accept_error == null ? '—' : `${(m.claim_accept_error * 100).toFixed(1)}%`],
            ['Coverage (test)', m.claim_coverage == null ? '—' : `${Math.round(m.claim_coverage * 100)}%`]].map(([k, v]) => (
            <div key={k} className="bg-card px-3 py-2.5">
              <dt className="text-[11px] uppercase tracking-wider text-muted">{k}</dt>
              <dd className="m-0 mt-0.5 font-medium tabular">{v}</dd>
            </div>
          ))}
        </dl>
      </div>
      {info.note && <p className="m-0 text-xs text-faint">{info.note}</p>}
    </ChartCard>
  )
}

export default function Analytics({ search }) {
  const datasets = useApi(() => api.datasets(), [])
  const [picked, setPicked] = useState(() => new URLSearchParams(search).get('dataset'))
  const datasetId = picked ?? pickDemo(datasets.data)?._id
  const stats = useApi(() => api.analytics(datasetId, 30), [datasetId], { enabled: Boolean(datasetId) })
  const calibration = useApi(() => api.trustInfo(), [])
  const s = stats.data
  const stageMs = s?.latency.stage_median_ms ?? {}
  const stageTotal = Object.values(stageMs).reduce((a, b) => a + (b || 0), 0)

  return (
    <main className="mx-auto flex max-w-[1440px] flex-col gap-8 px-8 pt-10 pb-28 lg:px-12">
      <div className="flex flex-wrap items-end justify-between gap-5">
        <div className="flex items-start gap-3">
          <div>
            <Display as="h1" className="text-[48px] leading-none sm:text-[56px]">Analytics</Display>
            <p className="mt-2.5 mb-0 max-w-[55ch] text-base leading-relaxed text-muted">
              Verification engine performance — decisions, trust calibration, response latency.
            </p>
          </div>
          <HelpButton topic="Analytics shows how the verification engine performs: how many answers are verified vs withheld, the distribution of trust scores, and how fast each step runs." />
        </div>
        {(datasets.data ?? []).length > 1 && (
          <label className="flex items-center gap-2.5 text-sm text-muted">
            Dataset
            <select value={datasetId ?? ''} onChange={(e) => setPicked(e.target.value)}
              className="h-10 rounded-[var(--radius-md)] border border-line-strong bg-card px-3 text-sm text-cotton">
              {(datasets.data ?? []).map((d) => <option key={d._id} value={d._id}>{d.name}</option>)}
            </select>
          </label>
        )}
      </div>

      {(datasets.loading || stats.loading) && !s ? <Skeleton className="h-48 w-full" /> : stats.error ? (
        <p role="alert" className="text-[#e0857c]">Could not load: {stats.error.message}</p>
      ) : datasets.data?.length === 0 ? (
        <p className="text-muted">No datasets yet.</p>
      ) : s && (
        <>
          {/* Key metrics */}
          <dl className="m-0 grid grid-cols-2 gap-px overflow-hidden rounded-[var(--radius-lg)] border border-border bg-border lg:grid-cols-3 xl:grid-cols-5">
            <StatCard label="Questions" value={s.totals.questions} sub="total asked" helpText="Total questions asked in this dataset over the selected period." />
            <StatCard label="Verified" value={pct(s.totals.decisions.ACCEPT, s.totals.questions)} sub={`${s.totals.decisions.ACCEPT} answers`} helpText="Percentage of answers fully verified by NLI — all claims supported by source passages." />
            <StatCard label="Withheld" value={pct(s.totals.decisions.BLOCK, s.totals.questions)} sub={`${s.totals.decisions.BLOCK} answers`} helpText="Answers withheld because one or more claims contradicted the source." />
            <StatCard label="Avg Trust" value={s.totals.avg_trust ?? '—'} sub="out of 100" helpText="Average trust score of answered questions (estimated chance the answer is correct). 80+ high, 50-79 medium, below 50 low." />
            <StatCard label="Median Time" value={seconds(s.totals.p50_ms)} sub={`p95: ${seconds(s.totals.p95_ms)}`} helpText="How long it takes to retrieve, generate, and verify an answer." />
          </dl>

          {/* Charts */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <CalibrationCard info={calibration.data} />
            <ChartCard title="Decisions per day" description="Withheld = contradicted by source."
              helpText="Stacked bars show how many questions were verified (green), warned (yellow), or withheld (red) each day.">
              {s.totals.questions ? <><DecisionBars data={s.per_day} /><DecisionLegend /></> : <Empty>No questions in this period.</Empty>}
            </ChartCard>

            <ChartCard title="Trust distribution" description="Scores in bins of 10."
              helpText="Histogram of trust scores of answered questions: 80+ high, 50-79 medium, below 50 low.">
              {s.trust_histogram.some(Boolean) ? (
                <><TrustHistogram bins={s.trust_histogram} /><Legend items={TRUST_BANDS.map((b) => [b.label, b.color])} /></>
              ) : <Empty>No scored answers.</Empty>}
            </ChartCard>

            <ChartCard title="Response time" description="Median and 95th percentile per day."
              helpText="Time from question to verified answer. The 8s target line shows the goal. The stage breakdown shows where time is spent: retrieval (search + rerank), LLM drafting and NLI verification."
              className="col-span-full">
              {s.latency.series.some((x) => x.p50 != null) ? (
                <>
                  <LatencyLines series={s.latency.series} />
                  <Legend items={[['Median', '#EDEBDD'], ['95th pct', '#A8A496']]} />
                  {stageTotal > 0 && (
                    <div className="flex flex-col gap-2.5">
                      <span className="text-sm text-muted">Median by stage, {seconds(stageTotal)} total</span>
                      <div className="flex h-4 gap-0.5 overflow-hidden rounded-full">
                        {Object.entries(stageMs).filter(([, v]) => v).map(([k, v]) => <span key={k} title={`${k} ${v} ms`} style={{ flex: `${v} 1 0`, background: STAGE_COLOR[k] }} />)}
                      </div>
                      <Legend items={Object.entries(stageMs).filter(([, v]) => v).map(([k, v]) => [`${k} ${seconds(v)}`, STAGE_COLOR[k]])} />
                    </div>
                  )}
                </>
              ) : <Empty>No timings.</Empty>}
            </ChartCard>
          </div>
        </>
      )}
    </main>
  )
}
