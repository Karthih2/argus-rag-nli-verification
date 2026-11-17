/** One answered question: decision banner, cited claims, score strip, feedback and details. */
import { useState } from 'react'
import { api } from '../api/client'
import { Icon } from '../components/icon'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Spinner } from '../components/ui/misc'
import { fixed, seconds } from '../lib/format'
import { cn } from '../lib/utils'
import { CLAIMS, DECISIONS, TONE } from '../lib/verdicts'

/** True for answers stored by the current pipeline (older records lack claims and score cards). */
export const isComplete = (q) => Boolean(q && Array.isArray(q.claims) && Array.isArray(q.evidence) && q.score_card)

const refNumber = (ref) => Number(String(ref).replace(/\D/g, '')) || ref

/** Page for a citation ref, from the answer's evidence list. */
function pageOf(evidence, ref) {
  return evidence.find((e) => e.ref === ref)?.page
}

export function DecisionBanner({ decision, trust, extra }) {
  const d = DECISIONS[decision] ?? DECISIONS.NO_SUPPORT
  return (
    <div className={cn('flex items-center gap-2.5 border-b px-5 py-3.5 text-[15px] font-medium', TONE[d.tone])}>
      <Icon name={d.icon} size={18} strokeWidth={2} />
      <span>{d.banner}</span>
      {extra && <span className="font-normal opacity-80">{extra}</span>}
      {trust != null && decision !== 'NO_SUPPORT' && (
        <span className="ml-auto font-normal">Trust <strong className="font-semibold tabular">{trust}</strong></span>
      )}
    </div>
  )
}

/** Claims as sentences, each underlined by its verdict and followed by citation chips. */
export function ClaimText({ claims, evidence, onCite, activeRef }) {
  return (
    <p className="m-0 text-[17px] leading-[1.8]">
      {claims.map((c, i) => {
        const style = CLAIMS[c.label] ?? CLAIMS.UNVERIFIED
        return (
          <span key={i}>
            <span
              title={`${style.label}, support ${fixed(c.support)}`}
              className="underline-claim"
              style={{
                backgroundImage: style.dashed
                  ? `linear-gradient(90deg, ${style.underline} 60%, transparent 0)`
                  : `linear-gradient(${style.underline}, ${style.underline})`,
                backgroundSize: style.dashed ? '8px 2px' : undefined,
                backgroundRepeat: style.dashed ? 'repeat-x' : undefined,
              }}
            >
              {c.text}
            </span>
            {c.cites.map((ref) => (
              <button
                key={ref}
                type="button"
                onClick={() => onCite?.(ref)}
                className={cn(
                  'mx-1 inline-block cursor-pointer rounded-full px-2 py-px align-[2px] text-xs font-semibold transition-colors',
                  activeRef === ref ? 'bg-cherry text-cotton' : 'bg-active text-cotton hover:bg-cherry',
                )}
              >
                {refNumber(ref)}
                {pageOf(evidence, ref) ? ` · p.${pageOf(evidence, ref)}` : ''}
              </button>
            ))}{' '}
          </span>
        )
      })}
    </p>
  )
}

function ScoreStrip({ result }) {
  const sc = result.score_card
  const c = sc.claims
  const total = c.supported + c.weak + c.unverified + c.contradicted
  const firstPage = result.evidence[0]?.page
  const cells = [
    ['Claims', `${c.supported} of ${total} supported`],
    ['Lowest support', fixed(sc.min_support)],
    ['Numbers, quotes', sc.numbers_ok && sc.quotes_ok ? 'Both match' : !sc.numbers_ok ? 'Number mismatch' : 'Quote missing'],
    ['Evidence', `${sc.evidence_types.join(', ') || '—'}${firstPage ? `, p.${firstPage}` : ''}`],
    ['Trust source', sc.calibration?.version ? `Learned v${sc.calibration.version}` : 'Heuristic fallback'],
  ]
  return (
    <dl className="m-0 grid grid-cols-[repeat(auto-fit,minmax(130px,1fr))] gap-px overflow-hidden rounded-[var(--radius-md)] border border-border bg-border text-[13px]">
      {cells.map(([k, v], i) => (
        <div key={k} className="bg-card px-3.5 py-3">
          <dt className="text-muted">{k}</dt>
          <dd className={cn('m-0 mt-1 text-[15px] font-medium', k === 'Numbers, quotes' && v === 'Both match' && 'text-ok')}>{v}</dd>
        </div>
      ))}
    </dl>
  )
}

const REASONS = ['Wrong number', 'Missing information', 'Wrong passage', 'Should have answered']

function Feedback({ queryId, initial }) {
  const [value, setValue] = useState(initial ?? null)
  const [asking, setAsking] = useState(false)
  const [busy, setBusy] = useState(false)
  async function send(v, reason) {
    setBusy(true)
    try {
      await api.feedback(queryId, v, reason)
      setValue(v)
      setAsking(false)
    } finally {
      setBusy(false)
    }
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button variant="secondary" size="icon" aria-label="Answer was right" aria-pressed={value === true} disabled={busy}
        className={value === true ? 'border-ok-line text-ok' : ''} onClick={() => send(true)}>
        <Icon name="thumbUp" size={16} />
      </Button>
      <Button variant="secondary" size="icon" aria-label="Answer was wrong" aria-pressed={value === false} disabled={busy}
        className={value === false ? 'border-cherry text-[#e0857c]' : ''} onClick={() => setAsking((a) => !a)}>
        <Icon name="thumbUp" size={16} className="rotate-180" />
      </Button>
      {asking && REASONS.map((r) => (
        <Button key={r} variant="outline" size="sm" disabled={busy} onClick={() => send(false, r)}>{r}</Button>
      ))}
      {value != null && !asking && <span className="text-[13px] text-muted">Thanks, this helps improve trust scoring.</span>}
    </div>
  )
}

function Details({ result }) {
  return (
    <div className="flex flex-col gap-4 border-t border-border px-6 py-5 text-[13px]">
      <table className="w-full border-collapse">
        <thead>
          <tr className="text-left text-muted">
            <th className="py-2 pr-3 font-medium">Claim</th><th className="py-2 pr-3 font-medium">Label</th>
            <th className="py-2 pr-3 text-right font-medium">Support</th><th className="py-2 pr-3 text-right font-medium">Contra</th>
            <th className="py-2 font-medium">Checks</th>
          </tr>
        </thead>
        <tbody>
          {result.claims.map((c, i) => (
            <tr key={i} className="border-t border-hover align-top">
              <td className="py-2 pr-3">{c.text}</td>
              <td className="py-2 pr-3 whitespace-nowrap">{CLAIMS[c.label]?.label}</td>
              <td className="py-2 pr-3 text-right tabular">{fixed(c.support)}</td>
              <td className="py-2 pr-3 text-right tabular">{fixed(c.contra)}</td>
              <td className="py-2 text-muted">
                {[c.checks.quote_match ? 'quote found' : 'no quote', c.checks.numbers_ok ? 'numbers ok' : c.checks.number_detail]
                  .filter(Boolean).join(', ')}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="m-0 font-mono text-xs text-faint">
        {Object.entries(result.latency_ms ?? {}).map(([k, v]) => `${k} ${v} ms`).join('  ')}
        {result.attempts?.length > 1 && `  repaired by ${result.attempts[1].model || 'the model'}`}
      </p>
    </div>
  )
}

/** A whole answered turn. */
export function AnswerTurn({ turn, risk, onCite, activeRef, selected, onSelect }) {
  const [open, setOpen] = useState(false)
  const result = { claims: [], evidence: [], ...turn, query_id: turn.query_id ?? turn._id, risk }
  if (!isComplete(turn)) result.score_card = null
  const blocked = result.decision === 'BLOCK'
  const noSupport = result.decision === 'NO_SUPPORT'
  return (
    <article className="flex flex-col gap-3.5" aria-label={`Answer to: ${result.question}`}>
      <div className="flex max-w-[80%] flex-col items-end gap-1.5 self-end">
        <p className="m-0 rounded-[14px_14px_4px_14px] bg-hover px-4 py-3 text-base">{result.question}</p>
      </div>
      <div
        onClick={onSelect}
        className={cn('overflow-hidden rounded-[16px] border bg-card transition-colors', blocked ? 'border-[#4a1a16]' : selected ? 'border-line-bright' : 'border-border')}
      >
        <DecisionBanner decision={result.decision} trust={result.trust} extra={result.score_card?.repaired ? '(repaired once)' : null} />
        <div className="flex flex-col gap-4 px-6 py-5">
          {blocked && result.blocked_reason && (
            <>
              <p className="m-0 text-base leading-relaxed text-soft">
                The draft said <span className="text-cotton line-through decoration-[#c0544a] decoration-2">{result.blocked_reason.draft_claim}</span>
                {result.blocked_reason.reason ? `, but ${result.blocked_reason.reason}.` : '.'} Only the evidence is shown.
              </p>
              <blockquote className="m-0 rounded-[12px] bg-cotton px-5 py-4 font-display text-[19px] leading-normal text-noir">
                <span className="mb-1.5 block font-sans text-xs text-graphite">Page {result.blocked_reason.page} says</span>
                {result.blocked_reason.evidence_text}
              </blockquote>
            </>
          )}
          {noSupport && (
            <p className="m-0 text-base text-soft">These documents don't answer that. The closest passages are in the evidence panel.</p>
          )}
          {!blocked && !noSupport && (
            <ClaimText claims={result.claims} evidence={result.evidence} onCite={onCite} activeRef={selected ? activeRef : null} />
          )}
          {result.score_card && !noSupport && !blocked && <ScoreStrip result={result} />}
          <div className="flex flex-wrap items-center gap-3">
            <Feedback queryId={result.query_id} initial={result.feedback?.value} />
            <span className="ml-auto text-[13px] text-muted tabular">{seconds(result.latency_ms?.total)}</span>
            {result.claims?.length > 0 && (
              <Button variant="ghost" size="sm" onClick={(e) => { e.stopPropagation(); setOpen((o) => !o) }} aria-expanded={open}>
                Details <Icon name="chevronDown" size={14} className={open ? 'rotate-180' : ''} />
              </Button>
            )}
          </div>
        </div>
        {open && <Details result={result} />}
      </div>
    </article>
  )
}

const STAGE_LABEL = {
  searching: () => 'Searching',
  reading: (d) => `Read ${d.passages} passages`,
  drafting: () => 'Drafting',
  checking: (d) => (d.claims ? `Checking ${d.claims} claims` : 'Checking claims'),
  repairing: () => 'Repairing one claim',
  done: () => 'Done',
}
export const stageText = (e) => (STAGE_LABEL[e.stage] ?? (() => e.stage))(e)

/** A question still being answered: the stages so far and skeleton lines. */
export function PendingTurn({ question, stages, error, onRetry }) {
  return (
    <article className="flex flex-col gap-3.5" aria-busy={!error}>
      <p className="m-0 max-w-[80%] self-end rounded-[14px_14px_4px_14px] bg-hover px-4 py-3 text-base">{question}</p>
      <div className="flex flex-col gap-4 rounded-[16px] border border-border bg-card px-6 py-5">
        <ol className="m-0 flex list-none flex-wrap gap-2 p-0 text-[13px]">
          {stages.map((s, i) => {
            const last = i === stages.length - 1 && !error
            return (
              <li key={i} className={cn('flex items-center gap-1.5 rounded-full border px-3 py-1.5', last ? 'border-line-bright bg-hover text-cotton' : 'border-border text-soft')}>
                {last ? <Spinner size={13} /> : <Icon name="check" size={13} strokeWidth={2.6} className="text-ok" />}
                {stageText(s)}
              </li>
            )
          })}
        </ol>
        {error ? (
          <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-[#e0857c]">
            {error}
            <Button variant="outline" size="sm" onClick={onRetry}>Try again</Button>
          </div>
        ) : (
          <>
            <div aria-hidden="true" className="flex flex-col gap-2.5">
              <span className="anim-shimmer h-3 w-[94%] rounded-full bg-line" />
              <span className="anim-shimmer delay-1 h-3 w-[86%] rounded-full bg-line" />
              <span className="anim-shimmer delay-2 h-3 w-[60%] rounded-full bg-line" />
            </div>
            <p className="m-0 text-[13px] text-faint">The answer appears once every claim has been checked.</p>
          </>
        )}
      </div>
    </article>
  )
}

export function DecisionBadge({ decision }) {
  const d = DECISIONS[decision] ?? DECISIONS.NO_SUPPORT
  return <Badge variant={d.tone}>{d.label}</Badge>
}
