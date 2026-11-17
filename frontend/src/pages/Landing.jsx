/** Landing: the product in one screen, a real checked answer from the demo set, how it works, and upload. */
import { useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/hooks'
import { Icon } from '../components/icon'
import { Button } from '../components/ui/button'
import { Display, Skeleton, Spinner } from '../components/ui/misc'
import { DropZone } from '../components/upload'
import { GridBackdrop, HeroArt, STEP_ART } from '../features/art'
import { ClaimText, DecisionBadge, isComplete } from '../features/answer'
import { pickDemo, startChat } from '../lib/chat'
import { fixed, plural } from '../lib/format'
import { Link } from '../lib/router'

const STEPS = [
  ['retrieve', 'Retrieve', 'Semantic and keyword search over your documents, reranked down to the 8 best passages.'],
  ['draft', 'Draft with quotes', 'The model answers in short claims. Each one cites a passage and copies the exact words it relies on.'],
  ['check', 'Check every claim', 'A language-inference model tests each claim against its passage. Numbers and quotations have to match exactly.'],
  ['decide', 'Decide', 'Supported answers are shown. Contradicted claims are withheld, and you see the evidence.'],
]

function AskBox({ demo }) {
  const [q, setQ] = useState('')
  const [busy, setBusy] = useState(false)
  async function go(question) {
    if (!question.trim() || !demo) return
    setBusy(true)
    await startChat(demo._id, [], question.trim()).finally(() => setBusy(false))
  }
  return (
    <form onSubmit={(e) => { e.preventDefault(); go(q) }} className="flex flex-col gap-3">
      <label htmlFor="landing-ask" className="text-sm text-graphite">Ask the {demo?.name ?? 'demo'} set your own question</label>
      <div className="flex items-center gap-3 rounded-[12px] border border-rule bg-paper py-2 pr-2 pl-4">
        <Icon name="search" className="text-graphite" />
        <input id="landing-ask" value={q} onChange={(e) => setQ(e.target.value)} placeholder="For example: how long are case records kept?"
          className="min-w-0 flex-1 border-0 bg-transparent text-base text-noir outline-none placeholder:text-[#8a867a]" />
        <Button type="submit" disabled={busy || !q.trim() || !demo} className="h-10">{busy ? <Spinner /> : 'Ask'}</Button>
      </div>
    </form>
  )
}

/** The newest verified answer from the demo set, shown exactly as Argus produced it. */
function LiveAnswer({ demo }) {
  const latest = useApi(() => api.queries({ datasetId: demo._id, decision: 'ACCEPT', complete: true, limit: 1 }), [demo._id])
  const id = latest.data?.items?.[0]?._id
  const full = useApi(() => api.query(id), [id], { enabled: Boolean(id) })
  const q = isComplete(full.data) ? full.data : null
  const quoteClaim = q?.claims?.find((c) => c.quote)
  const quoteItem = q?.evidence?.find((e) => quoteClaim?.cites.includes(e.ref))

  return (
    <div className="anim-float flex flex-col gap-6 rounded-[16px] bg-cotton p-8 text-left text-noir shadow-[0_30px_60px_-20px_rgba(0,0,0,.65),0_0_0_1px_#2e2c2a] sm:p-10">
      {latest.loading || (id && full.loading) ? (
        <div className="flex flex-col gap-3"><Skeleton className="h-8 w-3/4 bg-rule" /><Skeleton className="h-4 w-full bg-rule" /><Skeleton className="h-4 w-5/6 bg-rule" /></div>
      ) : q ? (
        <>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex min-w-0 flex-[1_1_480px] items-center gap-3.5 rounded-[12px] border border-rule bg-paper px-4 py-3.5">
              <Icon name="search" size={20} className="flex-none text-graphite" />
              <h2 className="m-0 font-display text-[28px] leading-tight font-semibold">{q.question}</h2>
            </div>
            <span className="text-sm text-graphite">{q.evidence?.[0]?.file_name}</span>
          </div>
          <ol className="m-0 flex list-none flex-wrap gap-2.5 p-0 text-sm">
            {[`Searched ${demo.document_count} documents`, `Read ${plural(q.evidence.length, 'passage')}`, `Drafted ${plural(q.claims.length, 'claim')}`, 'Checked each claim'].map((s, i) => (
              <li key={s} className={`anim-rise delay-${i + 1} flex items-center gap-2 rounded-full border border-rule bg-paper px-3.5 py-1.5`}>
                <Icon name="check" size={14} strokeWidth={2.4} className="text-ok-line" />{s}
              </li>
            ))}
          </ol>
          <div className="max-w-[72ch]"><ClaimText claims={q.claims} evidence={q.evidence} /></div>
          {quoteItem && (
            <blockquote className="m-0 rounded-[12px] border border-rule bg-paper px-5 py-4 font-display text-xl leading-normal">
              <span className="mb-1.5 block font-sans text-xs text-graphite">{quoteItem.section || quoteItem.type}, page {quoteItem.page}</span>
              <mark className="rounded-[3px] bg-ok-bg px-0.5 text-ok-ink">{quoteClaim.quote}</mark>
            </blockquote>
          )}
          <div className="anim-rise delay-6 flex flex-wrap items-center gap-5 border-t border-rule pt-5 text-[15px] text-graphite">
            <DecisionBadge decision={q.decision} />
            <span>Trust <strong className="font-semibold text-noir tabular">{q.trust}</strong></span>
            <span>Lowest support <strong className="font-semibold text-noir tabular">{fixed(q.score_card.min_support)}</strong></span>
            <span>Evidence: {q.score_card.evidence_types.join(', ')}</span>
            <Link to={`/chat/${q.session_id}`} className="ml-auto text-graphite hover:text-noir">Open this chat</Link>
          </div>
        </>
      ) : (
        <p className="m-0 font-display text-[28px] font-semibold">Ask the first question of the demo set.</p>
      )}
      <AskBox demo={demo} />
    </div>
  )
}

function ContentTiles() {
  const tile = 'flex flex-col gap-4.5 rounded-[14px] border border-border bg-card p-7 transition-colors hover:border-line-bright'
  return (
    <div className="grid grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-5">
      <div className={tile}>
        <div aria-hidden="true" className="grid h-32 grid-cols-2 content-center gap-3.5">
          {[[100, 86, 94, 70], [90, 80, 100, 60]].map((col, c) => (
            <div key={c} className="flex flex-col gap-2">
              {col.map((w, i) => <span key={i} className={`anim-read delay-${c * 4 + i + 1 > 6 ? 6 : c * 4 + i + 1} h-1.5 rounded-full bg-line-strong`} style={{ width: `${w}%` }} />)}
            </div>
          ))}
        </div>
        <h3 className="m-0 text-xl font-semibold">Text in reading order</h3>
        <p className="m-0 text-[15px] leading-relaxed text-soft">Two-column layouts stay in order and keep their headings.</p>
      </div>
      <div className={tile}>
        <div aria-hidden="true" className="flex h-32 flex-col justify-center text-[13px] text-muted">
          <div className="flex justify-between border-b border-line-strong py-2"><span>Type</span><span>Retention</span></div>
          {[['Complaints', '7 years'], ['Agreed action', '6 years'], ['Assessments', '3 years']].map(([a, b], i) => (
            <div key={a} className={`anim-row delay-${i + 1} flex justify-between border-b border-line py-2 text-cotton last:border-0`}><span>{a}</span><span>{b}</span></div>
          ))}
        </div>
        <h3 className="m-0 text-xl font-semibold">Tables as facts</h3>
        <p className="m-0 text-[15px] leading-relaxed text-soft">Each row is checked with its column names attached.</p>
      </div>
      <div className={tile}>
        <div aria-hidden="true" className="flex h-32 items-end gap-3.5 border-b border-line-strong px-2">
          {[['94%', '#EDEBDD'], ['30%', '#A8A496'], ['14%', '#810100'], ['52%', '#57534C']].map(([h, c], i) => (
            <span key={i} className={`anim-grow delay-${i + 1} flex-1 rounded-t-[4px]`} style={{ height: h, background: c }} />
          ))}
        </div>
        <h3 className="m-0 text-xl font-semibold">Charts described</h3>
        <p className="m-0 text-[15px] leading-relaxed text-soft">Printed labels are trusted; chart values are checked against the source.</p>
      </div>
      <div className={tile}>
        <div aria-hidden="true" className="flex h-32 flex-col justify-center gap-2.5">
          <div className="grid h-20 place-items-center rounded-[8px] border border-line-strong text-line-bright"><Icon name="image" size={40} strokeWidth={1.4} /></div>
          <span className="overflow-hidden font-mono text-xs whitespace-nowrap text-muted"><span className="anim-type inline-block overflow-hidden align-bottom">A crew member at an open rack…</span></span>
        </div>
        <h3 className="m-0 text-xl font-semibold">Photos, described</h3>
        <p className="m-0 text-[15px] leading-relaxed text-soft">Captions are extracted and checked.</p>
      </div>
    </div>
  )
}

export default function Landing({ onUpload }) {
  const datasets = useApi(() => api.datasets(), [])
  const demo = pickDemo(datasets.data)

  return (
    <main>
      <section className="relative overflow-hidden border-b border-border">
        <GridBackdrop />
        <HeroArt />
        <div className="relative mx-auto flex max-w-[1200px] flex-col items-center gap-7 px-6 pt-36 pb-28 text-center sm:px-8">
          <p className="m-0 inline-flex items-center gap-2.5 rounded-full border border-line-strong bg-noir px-3.5 py-1.5 text-[15px] text-muted">
            <span className="anim-pulse h-2 w-2 rounded-full bg-ok" />Claim-level verification for the documents you upload
          </p>
          <h1 className="m-0 max-w-[14ch] font-display text-[clamp(52px,7.4vw,104px)] leading-none font-semibold tracking-[-0.01em]">
            Answers from your documents, checked against the page.
          </h1>
          <p className="m-0 max-w-[58ch] text-xl leading-relaxed text-soft">
            Argus finds the passage behind every sentence it writes. Claims the source supports are shown with their quote. Claims it contradicts are withheld, and you see the page instead.
          </p>
          <div className="mt-2 flex flex-wrap justify-center gap-3.5">
            <Button size="lg" onClick={onUpload}><Icon name="upload" />Upload documents</Button>
            <Button size="lg" variant="outline" className="bg-noir" disabled={!demo} onClick={() => startChat(demo._id)}>Try the {demo ? 'demo set' : 'demo'}</Button>
          </div>
          <div className="mt-16 w-full max-w-[1060px]">
            {datasets.loading ? <Skeleton className="h-72 w-full rounded-[16px]" /> : demo ? (
              <LiveAnswer demo={demo} />
            ) : (
              <p className="m-0 text-muted">No datasets yet. Upload documents to create one, or run <code className="font-mono">python -m scripts.seed_demo</code> to add the NASA demo set.</p>
            )}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1200px] px-6 pt-32 pb-10 sm:px-8">
        <Display className="mb-3 text-[52px]">How each answer is checked</Display>
        <p className="m-0 mb-14 max-w-[60ch] text-lg leading-relaxed text-muted">Four steps run for every question. The answer only appears after the last one.</p>
        <ol className="m-0 grid list-none grid-cols-[repeat(auto-fit,minmax(250px,1fr))] gap-5 p-0">
          {STEPS.map(([key, title, body], i) => (
            <li key={key} className="flex flex-col gap-4 rounded-[14px] border border-border bg-card px-7 py-8 transition-colors hover:border-line-bright">
              {STEP_ART[key]}
              <span className="font-display text-[34px] leading-none font-semibold text-cherry">{i + 1}</span>
              <h3 className="m-0 text-xl font-semibold">{title}</h3>
              <p className="m-0 text-base leading-relaxed text-soft">{body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mx-auto max-w-[1200px] px-6 pt-28 pb-10 sm:px-8">
        <div className="mb-12 flex flex-wrap items-end justify-between gap-8">
          <Display className="max-w-[16ch] text-[52px]">Reads every kind of content on the page</Display>
          <p className="m-0 max-w-[44ch] text-[17px] leading-relaxed text-muted">Reports mix columns, tables, charts and photos. Each is extracted its own way, so the evidence exists before anything is checked.</p>
        </div>
        <ContentTiles />
      </section>

      <section id="upload" className="mx-auto max-w-[1200px] px-6 pt-28 pb-36 sm:px-8">
        <DropZone className="py-20">
          {STEP_ART.upload}
          <Display className="text-5xl">Drop PDF or Word files here</Display>
        </DropZone>
        {demo && (
          <p className="mt-5 mb-0 text-center text-sm text-faint">
            Or explore the demo set: {plural(demo.document_count, 'document')}, {plural(demo.page_count, 'page')}.{' '}
            <Link to={`/d/${demo._id}`} className="text-soft">Open it</Link>
          </p>
        )}
      </section>

      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-[1200px] flex-wrap justify-between gap-6 px-8 py-10 text-sm text-faint">
          <span><span className="mr-3.5 font-display text-[26px] font-semibold text-cotton">Argus</span>Built with Docling, MongoDB Atlas, DeBERTa and Groq</span>
          <span className="flex gap-6"><Link to="/datasets" className="text-faint hover:text-cotton">Datasets</Link><Link to="/analytics" className="text-faint hover:text-cotton">Analytics</Link></span>
        </div>
      </footer>
    </main>
  )
}
