/** History page: view, search, resume, and manage past chat sessions stored in MongoDB. */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/hooks'
import { Icon } from '../components/icon'
import { Button } from '../components/ui/button'
import { Display, Spinner } from '../components/ui/misc'
import { startChat } from '../lib/chat'
import { timeAgo } from '../lib/format'
import { Link, navigate } from '../lib/router'
import { cn } from '../lib/utils'

export default function History() {
  const [datasetFilter, setDatasetFilter] = useState('all')
  const [searchQuery, setSearchQuery] = useState('')
  const [deletingId, setDeletingId] = useState(null)

  const datasets = useApi(() => api.datasets(), [])
  const sessions = useApi(() => api.sessions(datasetFilter === 'all' ? undefined : datasetFilter), [datasetFilter])

  // Map dataset ID to dataset name
  const datasetMap = new Map()
  datasets.data?.forEach((d) => datasetMap.set(d._id, d.name))

  const allSessions = sessions.data ?? []
  const filtered = allSessions.filter((s) => {
    if (!searchQuery.trim()) return true
    const q = searchQuery.toLowerCase()
    const titleMatch = s.title?.toLowerCase().includes(q)
    const dsMatch = datasetMap.get(s.dataset_id)?.toLowerCase().includes(q)
    return titleMatch || dsMatch
  })

  async function handleDelete(e, sessionId) {
    e.stopPropagation()
    e.preventDefault()
    if (!confirm('Are you sure you want to delete this chat session and its history?')) return
    try {
      setDeletingId(sessionId)
      await api.deleteSession(sessionId)
      // If deleted session was active, clear it
      if (localStorage.getItem('argus_active_session') === sessionId) {
        localStorage.removeItem('argus_active_session')
      }
      await sessions.reload()
    } catch (err) {
      alert('Failed to delete session: ' + err.message)
    } finally {
      setDeletingId(null)
    }
  }

  async function handleStartNewChat() {
    const activeDs = datasetFilter !== 'all' ? datasetFilter : localStorage.getItem('argus_active_dataset') || datasets.data?.[0]?._id
    if (activeDs) {
      await startChat(activeDs)
    } else {
      navigate('/upload')
    }
  }

  return (
    <main className="mx-auto max-w-[1200px] px-6 py-8 sm:px-8 lg:px-12">
      {/* Top Header */}
      <div className="mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-cherry/15 text-cherry border border-cherry/30">
              <Icon name="clock" size={20} strokeWidth={2} />
            </div>
            <div>
              <Display as="h1" className="text-[32px] sm:text-[38px] text-cotton font-semibold leading-none">
                Conversation History
              </Display>
              <p className="m-0 mt-1.5 text-sm text-muted">
                All document questions, verified claims, and NLI records persisted to MongoDB.
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={handleStartNewChat}
            className="rounded-xl px-4 py-2 font-medium bg-cherry text-cotton hover:bg-maroon transition-all shadow-sm flex items-center gap-2 cursor-pointer"
          >
            <Icon name="plus" size={16} strokeWidth={2.2} />
            <span>New Chat</span>
          </Button>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="relative flex-1 max-w-md">
          <Icon name="search" size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-muted" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search past conversations by question or topic…"
            className="w-full rounded-xl border border-border bg-card py-2 pl-9 pr-4 text-sm text-cotton placeholder:text-faint outline-none focus:border-cotton/40 focus:bg-[#201d1c] transition-all"
          />
        </div>

        {/* Dataset Filter */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted flex items-center gap-1">
            <Icon name="database" size={13} />
            Dataset:
          </span>
          <select
            value={datasetFilter}
            onChange={(e) => setDatasetFilter(e.target.value)}
            className="rounded-xl border border-border bg-card px-3 py-1.5 text-xs text-cotton outline-none focus:border-cotton/40 cursor-pointer"
          >
            <option value="all">All Datasets ({datasets.data?.length ?? 0})</option>
            {datasets.data?.map((d) => (
              <option key={d._id} value={d._id}>
                {d.name} ({d.document_count} docs)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Loading state */}
      {sessions.loading && (
        <div className="flex items-center justify-center py-20">
          <Spinner size={24} />
          <span className="ml-3 text-sm text-muted">Loading saved conversation history…</span>
        </div>
      )}

      {/* Error state */}
      {sessions.error && (
        <div className="rounded-xl border border-cherry/40 bg-cherry/10 p-6 text-center text-sm text-[#e0857c]">
          Could not load conversation history: {sessions.error.message}
        </div>
      )}

      {/* Empty State */}
      {!sessions.loading && !sessions.error && filtered.length === 0 && (
        <div className="rounded-2xl border border-dashed border-border bg-card/40 p-12 text-center">
          <div className="mx-auto mb-4 grid h-12 w-12 place-items-center rounded-2xl bg-hover text-muted">
            <Icon name="clock" size={24} strokeWidth={1.5} />
          </div>
          <h3 className="m-0 text-lg font-semibold text-cotton">No conversations found</h3>
          <p className="mx-auto mt-2 max-w-md text-sm text-muted">
            {searchQuery
              ? 'No conversations matched your search query. Try clearing the search.'
              : 'You have not asked any questions yet or no sessions exist for the selected dataset.'}
          </p>
          <div className="mt-6 flex justify-center gap-3">
            <Button
              onClick={handleStartNewChat}
              className="rounded-xl px-4 py-2 text-sm font-medium bg-cherry text-cotton hover:bg-maroon transition-all cursor-pointer"
            >
              Start Asking Questions
            </Button>
            <Button
              variant="outline"
              onClick={() => navigate('/upload')}
              className="rounded-xl px-4 py-2 text-sm font-medium cursor-pointer"
            >
              Upload Documents
            </Button>
          </div>
        </div>
      )}

      {/* Session Cards Grid */}
      {!sessions.loading && !sessions.error && filtered.length > 0 && (
        <div className="grid gap-3.5">
          {filtered.map((s) => {
            const dsName = datasetMap.get(s.dataset_id) || 'Documents'
            const avgTrust = s.summary?.avg_trust ?? (s.trust_sum && s.turns ? Math.round(s.trust_sum / s.turns) : 0)
            const turnsCount = s.turns ?? 0
            const updatedDate = s.updated_at ? timeAgo(s.updated_at) : 'recently'
            const isDeleting = deletingId === s._id

            const trustColor =
              avgTrust >= 75
                ? 'text-ok bg-ok-line/15 border-ok-line/30'
                : avgTrust >= 50
                ? 'text-warn bg-warn/15 border-warn/30'
                : avgTrust > 0
                ? 'text-[#e0857c] bg-cherry/15 border-cherry/30'
                : 'text-muted bg-hover border-border'

            return (
              <div
                key={s._id}
                onClick={() => {
                  try {
                    localStorage.setItem('argus_active_session', s._id)
                    localStorage.setItem('argus_active_dataset', s.dataset_id)
                  } catch {}
                  navigate(`/dashboard/${s._id}`)
                }}
                className={cn(
                  'group relative flex flex-col justify-between gap-4 rounded-2xl border border-border bg-card p-5 transition-all hover:border-cotton/40 hover:bg-[#1a1716] cursor-pointer sm:flex-row sm:items-center shadow-sm',
                  isDeleting && 'opacity-50 pointer-events-none'
                )}
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                    <span className="flex items-center gap-1 rounded-md bg-hover px-2 py-0.5 text-[11px] font-medium text-soft">
                      <Icon name="database" size={11} className="text-ok" />
                      {dsName}
                    </span>
                    <span className="text-faint text-[11px]">·</span>
                    <span className="text-faint text-[11px]">{updatedDate}</span>
                    <span className="text-faint text-[11px]">·</span>
                    <span className="text-faint text-[11px]">{turnsCount} {turnsCount === 1 ? 'question' : 'questions'}</span>
                  </div>

                  <h3 className="m-0 text-base font-semibold text-cotton truncate group-hover:text-cherry transition-colors">
                    {s.title || 'Untitled Conversation'}
                  </h3>

                  {/* Verdict counts */}
                  <div className="mt-2.5 flex items-center gap-2 text-xs flex-wrap">
                    {s.summary?.ACCEPT > 0 && (
                      <span className="flex items-center gap-1 rounded-md bg-ok-line/10 border border-ok-line/20 px-2 py-0.5 text-[11px] text-ok">
                        <Icon name="check" size={11} /> {s.summary.ACCEPT} verified
                      </span>
                    )}
                    {s.summary?.WARN > 0 && (
                      <span className="flex items-center gap-1 rounded-md bg-warn/10 border border-warn/20 px-2 py-0.5 text-[11px] text-warn">
                        <Icon name="alert" size={11} /> {s.summary.WARN} need review
                      </span>
                    )}
                    {s.summary?.BLOCK > 0 && (
                      <span className="flex items-center gap-1 rounded-md bg-cherry/10 border border-cherry/20 px-2 py-0.5 text-[11px] text-[#e0857c]">
                        <Icon name="ban" size={11} /> {s.summary.BLOCK} withheld
                      </span>
                    )}
                  </div>
                </div>

                {/* Right side: Trust badge & Actions */}
                <div className="flex items-center gap-3 self-end sm:self-center flex-none">
                  {avgTrust > 0 && (
                    <div className={cn('flex flex-col items-end rounded-xl border px-3 py-1.5', trustColor)}>
                      <span className="text-[10px] uppercase font-semibold tracking-wider">Avg Trust</span>
                      <span className="text-lg font-bold tabular leading-tight">{avgTrust}</span>
                    </div>
                  )}

                  <div className="flex items-center gap-1.5">
                    <button
                      type="button"
                      title="Open chat"
                      className="flex items-center gap-1.5 rounded-xl border border-border bg-hover/80 px-3.5 py-2 text-xs font-medium text-cotton hover:border-cotton/40 hover:bg-hover transition-colors cursor-pointer"
                    >
                      <Icon name="chat" size={14} />
                      <span>Resume</span>
                    </button>

                    <button
                      type="button"
                      onClick={(e) => handleDelete(e, s._id)}
                      title="Delete conversation from MongoDB"
                      className="grid h-8 w-8 place-items-center rounded-xl border border-border text-faint hover:text-[#e0857c] hover:border-cherry/40 hover:bg-cherry/10 transition-colors cursor-pointer"
                    >
                      <Icon name="trash" size={14} />
                    </button>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </main>
  )
}
