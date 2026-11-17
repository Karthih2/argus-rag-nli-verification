/** A conversation: past chats on the left, verified answers in the middle, evidence on the right. */
import { useEffect, useRef, useState } from 'react'
import { api, ask } from '../api/client'
import { useApi } from '../api/hooks'
import { Icon } from '../components/icon'
import { PageState, TopBar } from '../components/TopBar'
import { Button } from '../components/ui/button'
import { Spinner, Textarea } from '../components/ui/misc'
import { AnswerTurn, PendingTurn, stageText } from '../features/answer'
import { EvidencePanel } from '../features/evidence'
import { useActivity } from '../lib/activity'
import { startChat } from '../lib/chat'
import { plural } from '../lib/format'
import { Link, navigate } from '../lib/router'
import { cn } from '../lib/utils'

const STAGE_PROGRESS = { searching: 0.15, reading: 0.3, drafting: 0.45, checking: 0.7, repairing: 0.85, done: 1 }

function Sidebar({ session, docs, sessions }) {
  const [starting, setStarting] = useState(false)
  const inChat = new Set(session.document_ids)
  const shown = (docs ?? []).filter((d) => !inChat.size || inChat.has(d._id))
  return (
    <aside aria-label="Chats" className="flex flex-[0_0_260px] flex-col gap-2 border-r border-border px-4 py-5 max-lg:hidden">
      <Button disabled={starting} onClick={() => { setStarting(true); startChat(session.dataset_id, session.document_ids).finally(() => setStarting(false)) }}>
        {starting ? <Spinner /> : <Icon name="plus" size={16} />}New chat
      </Button>
      <p className="mt-5 mb-1 px-2 text-[13px] text-faint">{inChat.size ? 'Documents in this chat' : 'Searching all documents'}</p>
      <ul className="m-0 mb-4 flex list-none flex-col gap-1.5 px-2 text-[13px] text-soft">
        {shown.map((d) => <li key={d._id} className="flex items-start gap-2"><Icon name="file" size={14} className="mt-0.5 flex-none text-faint" /><span>{d.metadata?.title || d.file.name}</span></li>)}
      </ul>
      <p className="mb-1 px-2 text-[13px] text-faint">Chats</p>
      {(sessions ?? []).map((s) => (
        <Link key={s._id} to={`/chat/${s._id}`} aria-current={s._id === session._id ? 'page' : undefined}
          className={cn('block truncate rounded-[8px] px-3 py-2 text-sm no-underline', s._id === session._id ? 'bg-hover text-cotton' : 'text-muted hover:bg-hover hover:text-cotton')}>
          {s.title || 'Untitled chat'}
        </Link>
      ))}
    </aside>
  )
}

export default function Chat({ params, search }) {
  const sid = params.sessionId
  const detail = useApi(() => api.session(sid), [sid])
  const session = detail.data?.session
  const datasetId = session?.dataset_id
  const ds = useApi(() => api.dataset(datasetId), [datasetId], { enabled: Boolean(datasetId) })
  const docs = useApi(() => api.documents(datasetId), [datasetId], { enabled: Boolean(datasetId) })
  const sessions = useApi(() => api.sessions(datasetId), [datasetId], { enabled: Boolean(datasetId) })
  const { setAnswering, setLastDone } = useActivity()

  const [input, setInput] = useState('')
  const [pending, setPending] = useState(null) // { question, stages, error }
  const [selected, setSelected] = useState(null) // query id shown in the evidence panel
  const [activeRef, setActiveRef] = useState(null)
  const bottom = useRef(null)
  const asked = useRef(false)
  const abort = useRef(null)

  const turns = detail.data?.turns ?? []
  const current = turns.find((t) => (t.query_id ?? t._id) === selected) ?? turns[turns.length - 1]

  function submit(question) {
    const q = question.trim()
    if (!q || pending) return
    setInput('')
    setPending({ question: q, stages: [{ stage: 'searching' }], error: null })
    abort.current = ask(sid, q, {
      onStage: (e) => {
        if (e.stage === 'done') return
        setPending((p) => p && { ...p, stages: [...p.stages.filter((s) => s.stage !== e.stage), e] })
        setAnswering({ title: stageText(e), meta: plural(turns.length + 1, 'question'), progress: STAGE_PROGRESS[e.stage] ?? 0.5, tone: 'busy' })
      },
      onResult: async (r) => {
        setAnswering(null)
        setLastDone({ title: r.decision === 'BLOCK' ? 'Answer withheld' : r.decision === 'NO_SUPPORT' ? 'Not in these documents' : 'Answer checked', meta: r.decision === 'NO_SUPPORT' ? '' : `trust ${r.trust}`, progress: 1, tone: r.decision === 'BLOCK' ? 'warn' : 'ok' })
        await detail.reload()
        sessions.reload()
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

  // A question passed in the URL (from the landing page or an example) is asked once.
  useEffect(() => {
    const q = new URLSearchParams(search).get('q')
    if (q && session && !asked.current) {
      asked.current = true
      navigate(`/chat/${sid}`, { replace: true })
      submit(q)
    }
  }) // runs after each render until the session has loaded

  useEffect(() => () => abort.current?.(), [])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [turns.length, pending?.stages.length])

  const summary = session?.summary
  return (
    <>
      <TopBar
        crumbs={[{ label: 'Datasets', to: '/datasets' }, { label: ds.data?.name ?? '…', to: datasetId && `/d/${datasetId}` }, { label: session?.title || 'New chat' }]}
        right={session?.turns > 0 && (
          <span className="text-[13px] text-muted tabular">
            {plural(session.turns, 'question')}: {summary.ACCEPT} verified, {summary.ACCEPT_LOW_CONFIDENCE} partly, {summary.BLOCK} withheld. Average trust {summary.avg_trust}
          </span>
        )}
      />
      <PageState loading={detail.loading && !detail.data} error={detail.error}>
        {session && (
          <div className="flex flex-wrap items-stretch">
            <Sidebar session={session} docs={docs.data} sessions={sessions.data} />
            <main className="flex min-w-0 flex-[999_1_560px] flex-col gap-10 px-6 pt-8 pb-12 sm:px-10">
              {turns.length === 0 && !pending && (
                <div className="flex flex-col gap-2 pt-10">
                  <h1 className="m-0 font-display text-5xl font-semibold">Ask {ds.data?.name ?? 'these documents'}</h1>
                  <p className="m-0 text-muted">Every claim in the answer is checked against the page before you see it.</p>
                </div>
              )}
              {turns.map((t) => {
                const qid = t.query_id ?? t._id
                const isCurrent = current && qid === (current.query_id ?? current._id)
                return (
                  <AnswerTurn key={qid} turn={t} risk={ds.data?.settings?.risk_alpha_accept} selected={isCurrent} activeRef={activeRef}
                    onSelect={() => { setSelected(qid); if (!isCurrent) setActiveRef(null) }}
                    onCite={(ref) => { setSelected(qid); setActiveRef(ref) }} />
                )
              })}
              {pending && <PendingTurn {...pending} onRetry={() => { const q = pending.question; setPending(null); setTimeout(() => submit(q)) }} />}
              <form ref={bottom} onSubmit={(e) => { e.preventDefault(); submit(input) }} className="sticky bottom-28 z-10 -mx-2 flex flex-col gap-2.5 rounded-[16px] bg-noir/95 px-2 pt-2 pb-1">
                <label htmlFor="ask" className="text-[13px] text-faint">{turns.length ? 'Ask a follow-up' : 'Your question'}</label>
                <div className="flex items-end gap-2.5 rounded-[14px] border border-line-strong bg-card py-2.5 pr-2.5 pl-4.5 focus-within:border-muted">
                  <Textarea id="ask" rows={2} value={input} onChange={(e) => setInput(e.target.value)} disabled={Boolean(pending)}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit(input) } }}
                    placeholder={turns.length ? 'For example: and what about the next table?' : 'Ask about these documents'} />
                  <Button type="submit" disabled={Boolean(pending) || !input.trim()}>{pending ? <Spinner /> : 'Ask'}</Button>
                </div>
              </form>
            </main>
            <aside aria-label="Evidence" className="flex min-w-0 flex-[1_1_420px] flex-col gap-4 border-l border-border bg-[#1b1919] px-6 pt-6 pb-12">
              <div className="flex items-baseline justify-between gap-3">
                <h2 className="m-0 font-display text-[28px] font-semibold">Evidence</h2>
                {current && <span className="text-[13px] text-faint">{plural(current.evidence?.length ?? 0, 'passage')}</span>}
              </div>
              {current && <p className="m-0 -mt-2 truncate text-[13px] text-muted">For: {current.question}</p>}
              <EvidencePanel turn={current} activeRef={activeRef} onRef={setActiveRef} />
            </aside>
          </div>
        )}
      </PageState>
    </>
  )
}
