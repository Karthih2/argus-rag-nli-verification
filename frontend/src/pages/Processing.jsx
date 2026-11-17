/** Processing page: shows document parsing, embedding, and indexing progress. */
import { useEffect } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/hooks'
import { Icon } from '../components/icon'
import { HelpButton } from '../components/Navbar'
import { Display, Spinner } from '../components/ui/misc'
import { startChat } from '../lib/chat'
import { plural } from '../lib/format'
import { navigate } from '../lib/router'
import { cn } from '../lib/utils'

const BUSY = ['queued', 'parsing', 'embedding', 'indexing']

const PIPELINE = [
  { key: 'parsing', icon: 'file', label: 'Parsing Documents', desc: 'Reading pages, extracting text, tables, charts and photos' },
  { key: 'embedding', icon: 'layers', label: 'Creating Embeddings', desc: 'Generating BGE vector embeddings for semantic search' },
  { key: 'indexing', icon: 'database', label: 'Storing & Indexing', desc: 'Building MongoDB Atlas vector and text search indexes' },
  { key: 'ready', icon: 'check', label: 'Ready', desc: 'Documents processed and ready for verified Q&A' },
]
const STEP_ORDER = ['queued', 'parsing', 'embedding', 'indexing', 'ready']

function getStepIndex(status) {
  const idx = STEP_ORDER.indexOf(status)
  return idx >= 0 ? idx : 0
}

function StepIndicator({ step, index, currentStep, totalSteps }) {
  const done = currentStep > index + 1
  const active = currentStep === index + 1
  return (
    <div className="flex items-center gap-5">
      <div className={cn(
        'grid h-16 w-16 flex-none place-items-center rounded-2xl border-2 transition-all',
        done ? 'border-ok-line bg-ok-line/15 text-ok' : active ? 'border-cotton bg-hover text-cotton' : 'border-line-strong bg-noir text-faint',
      )}>
        {done ? <Icon name="check" size={26} strokeWidth={2.4} /> : active ? <Spinner size={24} /> : <Icon name={step.icon} size={26} />}
      </div>
      <div className="flex-1">
        <p className={cn('m-0 text-lg font-semibold', active ? 'text-cotton' : done ? 'text-ok' : 'text-faint')}>{step.label}</p>
        <p className={cn('m-0 mt-0.5 text-sm', active || done ? 'text-muted' : 'text-faint')}>{step.desc}</p>
      </div>
      {done && <span className="text-sm font-medium text-ok">Complete</span>}
      {active && <span className="text-sm font-medium text-cotton">In progress…</span>}
    </div>
  )
}

function ProgressBar({ current, total }) {
  const pct = total > 0 ? (current / total) * 100 : 0
  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-between text-sm">
        <span className="text-muted">Overall progress</span>
        <span className="font-medium tabular text-cotton">{Math.round(pct)}%</span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-line">
        <div className="h-full rounded-full bg-cherry transition-[width] duration-700" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function Processing({ params }) {
  const id = params.id
  const ds = useApi(() => api.dataset(id), [id], { poll: 3000 })
  const docs = useApi(() => api.documents(id), [id], { poll: 3000 })

  const processing = (docs.data ?? []).filter((d) => BUSY.includes(d.processing.status))
  const ready = (docs.data ?? []).filter((d) => d.processing.status === 'ready')
  const failed = (docs.data ?? []).filter((d) => d.processing.status === 'failed')
  const allDone = docs.data?.length > 0 && processing.length === 0

  // Auto-redirect when all done
  useEffect(() => {
    if (!allDone || !ready.length) return
    const t = setTimeout(async () => {
      await startChat(id, ready.map((d) => d._id))
    }, 1500)
    return () => clearTimeout(t)
  }, [allDone, ready, id])

  // Compute overall progress
  const totalSteps = (docs.data?.length ?? 0) * 4 // 4 steps per doc
  const completedSteps = (docs.data ?? []).reduce((sum, d) => sum + getStepIndex(d.processing.status), 0)

  return (
    <main className="mx-auto max-w-[800px] px-6 pt-12 pb-28 sm:px-8">
      <div className="mb-10 flex items-start justify-between gap-4">
        <div>
          <Display as="h1" className="text-[44px] sm:text-[52px]">
            {allDone ? 'Processing Complete' : 'Processing Documents'}
          </Display>
          <p className="mt-3 mb-0 text-lg text-muted">
            {allDone
              ? `${plural(ready.length, 'document')} ready. Redirecting to dashboard…`
              : `Processing ${plural(docs.data?.length ?? 0, 'document')}. You'll be redirected when ready.`}
          </p>
        </div>
        <HelpButton topic="Documents go through 4 stages: (1) Parsing — Docling reads every page, extracting text, tables, charts and photos. (2) Embedding — BGE model creates vector representations. (3) Indexing — MongoDB Atlas builds vector and text search indexes. (4) Ready — you can start asking questions." />
      </div>

      {/* Overall progress */}
      <ProgressBar current={completedSteps} total={totalSteps} />

      {/* Per-document progress */}
      <div className="mt-10 flex flex-col gap-6">
        {(docs.data ?? []).map((doc) => {
          const currentStep = getStepIndex(doc.processing.status)
          const isFailed = doc.processing.status === 'failed'
          return (
            <div key={doc._id} className={cn(
              'rounded-[var(--radius-lg)] border p-6',
              isFailed ? 'border-[#4a1a16] bg-[#1d1514]' : 'border-border bg-card',
            )}>
              {/* Doc header */}
              <div className="mb-6 flex items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="grid h-10 w-10 place-items-center rounded-lg bg-hover text-muted">
                    <Icon name="file" size={20} />
                  </div>
                  <div>
                    <p className="m-0 text-[17px] font-semibold text-cotton">{doc.metadata?.title || doc.file.name}</p>
                    <p className="m-0 text-xs text-faint">{doc.file.name} · {doc.metadata?.page_count ?? '?'} pages</p>
                  </div>
                </div>
                {doc.processing.status === 'ready' && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-ok-line/20 px-3 py-1 text-xs font-medium text-ok">
                    <Icon name="check" size={12} strokeWidth={2.4} />Ready
                  </span>
                )}
                {isFailed && (
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-cherry/20 px-3 py-1 text-xs font-medium text-[#e0857c]">
                    <Icon name="alert" size={12} />Failed
                  </span>
                )}
              </div>

              {/* Pipeline steps */}
              {isFailed ? (
                <p className="m-0 text-sm text-[#e0857c]">{doc.processing.error || 'Processing failed. Try uploading again.'}</p>
              ) : (
                <div className="flex flex-col gap-5">
                  {PIPELINE.map((step, i) => (
                    <StepIndicator key={step.key} step={step} index={i} currentStep={currentStep} totalSteps={PIPELINE.length} />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* All done message */}
      {allDone && ready.length > 0 && (
        <div className="mt-10 flex flex-col items-center gap-4 rounded-[var(--radius-lg)] border border-ok-line/30 bg-ok-line/5 px-8 py-10 text-center">
          <div className="grid h-16 w-16 place-items-center rounded-2xl bg-ok-line/20 text-ok">
            <Icon name="check" size={32} strokeWidth={2} />
          </div>
          <Display className="text-3xl text-ok">All documents processed</Display>
          <p className="m-0 text-muted">Your documents are indexed and ready for verified questions.</p>
          <button
            type="button"
            onClick={() => startChat(id, ready.map((d) => d._id))}
            className="mt-2 inline-flex cursor-pointer items-center gap-2 rounded-xl bg-cherry px-6 py-3 text-base font-semibold text-cotton shadow-lg transition-colors hover:bg-maroon"
          >
            Start Asking Questions →
          </button>
        </div>
      )}

      {/* Failed all */}
      {allDone && ready.length === 0 && failed.length > 0 && (
        <div className="mt-10 flex flex-col items-center gap-4 rounded-[var(--radius-lg)] border border-[#4a1a16] bg-[#1d1514] px-8 py-10 text-center">
          <Display className="text-3xl text-[#e0857c]">Processing failed</Display>
          <p className="m-0 text-muted">All documents failed to process. Please try uploading again.</p>
          <button type="button" onClick={() => navigate('/upload')} className="mt-2 cursor-pointer text-sm text-cotton underline underline-offset-4 hover:text-white">
            Upload again
          </button>
        </div>
      )}

      {/* Loading state */}
      {!docs.data && (
        <div className="flex flex-col items-center gap-4 py-20 text-center">
          <Spinner size={28} />
          <p className="m-0 text-lg text-muted">Loading document status…</p>
        </div>
      )}
    </main>
  )
}
