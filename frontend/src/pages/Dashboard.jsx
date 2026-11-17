/** Dashboard: main workspace — stats, question bar, results with NLI scores, evidence panel. */
import { useEffect, useRef, useState } from 'react'
import { api, ask } from '../api/client'
import { useApi } from '../api/hooks'
import { Icon } from '../components/icon'
import { HelpButton } from '../components/Navbar'
import { Button } from '../components/ui/button'
import { Display, Spinner, Textarea } from '../components/ui/misc'
import { AnswerTurn, PendingTurn, stageText } from '../features/answer'
import { EvidencePanel } from '../features/evidence'
import { useActivity } from '../lib/activity'
import { startChat } from '../lib/chat'
import { plural } from '../lib/format'
import { navigate } from '../lib/router'
import { cn } from '../lib/utils'

const STAGE_PROGRESS = { searching: 0.15, reading: 0.3, drafting: 0.45, checking: 0.7, repairing: 0.85, done: 1 }

/* ───── Stats cards at top ───── */

function StatCard({ icon, label, value, helpText }) {
  return (
    <div className="relative flex flex-col gap-2 rounded-[var(--radius-lg)] border border-border bg-card px-6 py-5">
      <div className="flex items-center justify-between">
        <div className="grid h-10 w-10 place-items-center rounded-lg bg-hover text-muted">
          <Icon name={icon} size={20} strokeWidth={1.5} />
        </div>
        {helpText && <HelpButton topic={helpText} />}
      </div>
      <span className="text-[36px] font-semibold leading-none tabular text-cotton">{value}</span>
      <span className="text-sm text-muted">{label}</span>
    </div>
  )
}

function DashboardStats({ ds, docs }) {
  const totalChunks = docs.reduce((s, d) => s + (d.stats?.chunks ?? 0), 0)
  const totalTables = docs.reduce((s, d) => s + (d.stats?.tables ?? 0), 0)
  const totalImages = docs.reduce((s, d) => s + ((d.stats?.charts ?? 0) + (d.stats?.photos ?? 0)), 0)

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
      <StatCard icon="file" label="Documents" value={ds.document_count} helpText="Total number of uploaded documents in this dataset." />
      <StatCard icon="layers" label="Pages" value={ds.page_count} helpText="Total pages across all documents." />
      <StatCard icon="hash" label="Chunks" value={totalChunks} helpText="Searchable text chunks created from your documents. Each chunk is an embeddable unit used for retrieval." />
      <StatCard icon="table" label="Tables" value={totalTables} helpText="Tables extracted from documents. Each row becomes a verifiable fact with column headers attached." />
      <StatCard icon="image" label="Images" value={totalImages} helpText="Charts and photos extracted. Labels are OCR'd and checked against source text." />
    </div>
  )
}

/* ───── Results display with layered NLI scoring ───── */

function ResultsSummary({ result }) {
  if (!result) return null
  const sc = result.score_card
  const noSupport = result.decision === 'NO_SUPPORT'
  const blocked = result.decision === 'BLOCK'

  // Always show verdict panel — even without score_card
  const trust = result.trust ?? 0
  const c = sc?.claims ?? { supported: 0, weak: 0, unverified: 0, contradicted: 0 }
  const total = c.supported + c.weak + c.unverified + c.contradicted

  const DECISIONS = {
    ACCEPT: { label: 'Verified', color: 'text-ok', icon: 'check', desc: 'Answer verified — all claims supported by source passages' },
    PARTIAL: { label: 'Partial', color: 'text-warn', icon: 'alert', desc: 'Some claims supported, some uncertain or missing evidence' },
    BLOCK: { label: 'Withheld', color: 'text-[#e0857c]', icon: 'ban', desc: 'Answer withheld — contains claims that contradict the source' },
    NO_SUPPORT: { label: 'No Support', color: 'text-muted', icon: 'search', desc: 'No relevant passages found in documents for this question' },
    LOW_CONF: { label: 'Low Confidence', color: 'text-warn', icon: 'alert', desc: 'Answer generated but confidence is too low for verification' },
  }
  const verdict = DECISIONS[result.decision] ?? DECISIONS.NO_SUPPORT

  const claimItems = [
    { label: 'Entailed', value: c.supported, color: 'text-ok', bg: 'bg-ok-line/20', icon: 'check' },
    { label: 'Weak', value: c.weak, color: 'text-warn', bg: 'bg-warn/20', icon: 'alert' },
    { label: 'Not Found', value: c.unverified, color: 'text-muted', bg: 'bg-hover', icon: 'search' },
    { label: 'Contradicted', value: c.contradicted, color: 'text-[#e0857c]', bg: 'bg-cherry/20', icon: 'ban' },
  ]

  return (
    <div className="rounded-[var(--radius-lg)] border border-border bg-card p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="m-0 flex items-center gap-2 text-lg font-semibold">
          <Icon name="shield" size={18} className="text-cherry" />
          Verification Result
        </h3>
        <HelpButton topic="NLI verification checks each claim in the answer against the source passages. Entailed = fully supported. Contradicted = conflicts with the source. Trust score is a calibrated probability the answer is correct." />
      </div>

      {/* Verdict + Trust */}
      <div className="mb-5 flex items-center gap-6">
        <div className="flex flex-col items-center gap-1.5">
          <span className={cn(
            'text-[52px] font-semibold leading-none tabular',
            trust >= 80 ? 'text-ok' : trust >= 60 ? 'text-warn' : 'text-[#e0857c]',
          )}>{trust || '—'}</span>
          <span className="text-sm text-muted">Trust Score</span>
        </div>
        <div className="h-16 w-px bg-border" />
        <div className="flex flex-1 flex-col gap-3">
          {/* Decision verdict */}
          <div className={cn('flex items-center gap-2 rounded-[var(--radius-sm)] px-3 py-2.5', verdict.color === 'text-ok' ? 'bg-ok-line/15' : verdict.color === 'text-warn' ? 'bg-warn/15' : verdict.color === 'text-[#e0857c]' ? 'bg-cherry/15' : 'bg-hover')}>
            <Icon name={verdict.icon} size={16} className={verdict.color} />
            <span className={cn('text-base font-semibold', verdict.color)}>{verdict.label}</span>
            <span className="text-xs text-muted">— {verdict.desc}</span>
          </div>
          {/* Claim breakdown (only when we have score_card) */}
          {sc && total > 0 && (
            <div className="flex flex-wrap gap-2.5">
              {claimItems.filter(it => it.value > 0).map((it) => (
                <div key={it.label} className={cn('flex items-center gap-1.5 rounded-[var(--radius-sm)] px-2.5 py-1.5', it.bg)}>
                  <Icon name={it.icon} size={13} className={it.color} />
                  <span className={cn('text-lg font-semibold tabular', it.color)}>{it.value}</span>
                  <span className="text-xs text-muted">{it.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Score bar — only with claim data */}
      {sc && total > 0 && (
        <div className="flex flex-col gap-2">
          <div className="flex h-3 gap-0.5 overflow-hidden rounded-full">
            {c.supported > 0 && <span className="rounded-l-full bg-ok-line" style={{ flex: c.supported }} />}
            {c.weak > 0 && <span className="bg-warn" style={{ flex: c.weak }} />}
            {c.unverified > 0 && <span className="bg-line-bright" style={{ flex: c.unverified }} />}
            {c.contradicted > 0 && <span className="rounded-r-full bg-cherry" style={{ flex: c.contradicted }} />}
          </div>
          <div className="flex justify-between text-xs text-faint">
            <span>{c.supported} of {total} claims supported</span>
            <span>Numbers {sc.numbers_ok ? '✓' : '✗'} · Quotes {sc.quotes_ok ? '✓' : '✗'}</span>
          </div>
        </div>
      )}

      {/* No support message */}
      {noSupport && !sc && (
        <p className="m-0 rounded-[var(--radius-sm)] bg-hover px-4 py-3 text-sm text-muted">
          No matching passages found in your documents. Try rephrasing, or check that the relevant document was uploaded.
        </p>
      )}
    </div>
  )
}

/* ───── Main Dashboard ───── */

export default function Dashboard({ params, search }) {
  const sid = params.sessionId
  const detail = useApi(() => api.session(sid), [sid])
  const session = detail.data?.session
  const datasetId = session?.dataset_id
  const ds = useApi(() => api.dataset(datasetId), [datasetId], { enabled: Boolean(datasetId) })
  const docs = useApi(() => api.documents(datasetId), [datasetId], { enabled: Boolean(datasetId) })
  const { setAnswering, setLastDone } = useActivity()

  const [input, setInput] = useState('')
  const [pending, setPending] = useState(null)
  const [selected, setSelected] = useState(null)
  const [activeRef, setActiveRef] = useState(null)
  const bottom = useRef(null)
  const asked = useRef(false)
  const abort = useRef(null)
  const textareaRef = useRef(null)

  const autoResize = (el) => { if (!el) return; el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px' }

  const turns = detail.data?.turns ?? []
  const current = turns.find((t) => (t.query_id ?? t._id) === selected) ?? turns[turns.length - 1]

  function submit(question) {
    const q = question.trim()
    if (!q || pending) return
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    setPending({ question: q, stages: [{ stage: 'searching' }], error: null })
    abort.current = ask(sid, q, {
      onStage: (e) => {
        if (e.stage === 'done') return
        setPending((p) => p && { ...p, stages: [...p.stages.filter((s) => s.stage !== e.stage), e] })
        setAnswering({ title: stageText(e), meta: plural(turns.length + 1, 'question'), progress: STAGE_PROGRESS[e.stage] ?? 0.5, tone: 'busy' })
      },
      onResult: async (r) => {
        setAnswering(null)
        setLastDone({ title: r.decision === 'BLOCK' ? 'Answer withheld' : r.decision === 'NO_SUPPORT' ? 'Not in documents' : 'Answer checked', meta: r.decision === 'NO_SUPPORT' ? '' : `trust ${r.trust}`, progress: 1, tone: r.decision === 'BLOCK' ? 'warn' : 'ok' })
        await detail.reload()
        setSelected(r.query_id)
        setActiveRef(r.claims?.[0]?.highlight?.ref ?? r.evidence?.[0]?.ref ?? null)
        setPending(null)
      },
      onError: (msg) => {
        setAnswering(null)
        setPending((p) => p && { ...p, error: msg })
      },
    })
  }

  useEffect(() => {
    const q = new URLSearchParams(search).get('q')
    if (q && session && !asked.current) {
      asked.current = true
      navigate(`/dashboard/${sid}`, { replace: true })
      submit(q)
    }
  })

  useEffect(() => () => abort.current?.(), [])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [turns.length, pending?.stages.length])

  if (detail.loading && !detail.data) {
    return <main className="flex items-center justify-center py-28"><Spinner size={28} /><span className="ml-3 text-muted">Loading dashboard…</span></main>
  }
  if (detail.error) {
    return <main className="mx-auto max-w-[800px] px-8 py-16"><p role="alert" className="text-[#e0857c]">Could not load: {detail.error.message}</p></main>
  }
  if (!session) return null

  return (
    <div className="flex h-[calc(100vh-57px)] overflow-hidden">
      {/* ── Left: Evidence Panel ── */}
      <aside aria-label="Evidence" className="flex w-[420px] flex-none flex-col gap-4 overflow-y-auto border-r border-border bg-[#1a1818] px-6 pt-6 pb-10 max-lg:hidden xl:w-[480px]">
        <div className="flex items-center justify-between gap-3">
          <h2 className="m-0 flex items-center gap-2 font-display text-2xl font-semibold">
            <Icon name="eye" size={20} className="text-cherry" />
            Evidence
          </h2>
          <div className="flex items-center gap-2">
            {current && <span className="text-xs text-faint">{plural(current.evidence?.length ?? 0, 'passage')}</span>}
            <HelpButton topic="Evidence shows the source passages used to verify the answer. Each chunk is ranked by relevance. The passage view highlights the exact quote that supports or contradicts a claim. Color coding: green = supports, red = contradicts, gray = no match." />
          </div>
        </div>
        {current && <p className="m-0 -mt-1 truncate text-xs text-muted">For: {current.question}</p>}
        <EvidencePanel turn={current} activeRef={activeRef} onRef={setActiveRef} />
      </aside>

      {/* ── Main content ── */}
      <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
        {/* Stats strip */}
        {ds.data && docs.data && (
          <div className="border-b border-border px-6 pt-5 pb-5 sm:px-8">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <Display as="h1" className="text-[32px] sm:text-[40px]">{ds.data.name}</Display>
                {ds.data.description && <p className="m-0 mt-1 text-sm text-muted">{ds.data.description}</p>}
              </div>
              <HelpButton topic="This dashboard shows your document dataset stats and lets you ask verified questions. The question goes through RAG retrieval, LLM generation, and NLI verification. Results show trust scores and claim-level verification." />
            </div>
            <DashboardStats ds={ds.data} docs={docs.data} />
          </div>
        )}

        {/* Question bar */}
        <div className="border-b border-border bg-noir/50 px-6 py-4 sm:px-8">
          <form onSubmit={(e) => { e.preventDefault(); submit(input) }} className="mx-auto max-w-[900px]">
            <label htmlFor="ask" className="mb-2 flex items-center gap-2 text-sm font-medium text-soft">
              <Icon name="search" size={14} />Ask about your documents
              <HelpButton topic="Type a question. Argus retrieves relevant passages, generates an answer with citations, then verifies every claim using NLI. Supported answers are shown; contradicted ones are withheld." className="ml-1" />
            </label>
            <div className="flex items-end gap-3 rounded-[var(--radius-md)] border border-line-strong bg-card py-2.5 pr-2.5 pl-5 transition-colors focus-within:border-line-bright focus-within:ring-1 focus-within:ring-line-bright/30">
              <Textarea id="ask" rows={1} value={input} onChange={(e) => { setInput(e.target.value); autoResize(e.target) }} disabled={Boolean(pending)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(input) } }}
                placeholder="What would you like to know?"
                ref={textareaRef}
                className="max-h-[160px] text-[15px] [&]:outline-none [&]:focus-visible:outline-none" />
              <Button type="submit" size="sm" disabled={Boolean(pending) || !input.trim()}>
                {pending ? <Spinner /> : <Icon name="search" size={16} />}
                Ask
              </Button>
            </div>
          </form>
        </div>

        {/* Answers area */}
        <div className="mx-auto flex w-full max-w-[900px] flex-1 flex-col gap-6 px-6 pt-6 pb-10 sm:px-8">
          {turns.length === 0 && !pending && (
            <div className="flex flex-col items-center gap-4 py-16 text-center">
              <div className="grid h-20 w-20 place-items-center rounded-2xl border border-line-strong bg-hover text-muted">
                <Icon name="chat" size={36} strokeWidth={1.3} />
              </div>
              <Display className="text-3xl sm:text-4xl">Ask your first question</Display>
              <p className="m-0 max-w-[45ch] text-base text-muted">Type a question above. Every claim in the answer is verified against your documents using NLI.</p>
            </div>
          )}

          {turns.map((t) => {
            const qid = t.query_id ?? t._id
            const isCurrent = current && qid === (current.query_id ?? current._id)
            return (
              <div key={qid} className="flex flex-col gap-4">
                <AnswerTurn turn={t} risk={ds.data?.settings?.risk_alpha_accept} selected={isCurrent} activeRef={activeRef}
                  onSelect={() => { setSelected(qid); if (!isCurrent) setActiveRef(null) }}
                  onCite={(ref) => { setSelected(qid); setActiveRef(ref) }} />
                {/* Layered NLI results below each answer */}
                {isCurrent && <ResultsSummary result={t} />}
              </div>
            )
          })}

          {pending && <PendingTurn {...pending} onRetry={() => { const q = pending.question; setPending(null); setTimeout(() => submit(q)) }} />}
          <div ref={bottom} />
        </div>
      </main>
    </div>
  )
}
