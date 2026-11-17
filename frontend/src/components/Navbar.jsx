/** Top navigation bar with active dataset indicator and persistent session routing. */
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/hooks'
import { startChat } from '../lib/chat'
import { Link } from '../lib/router'
import { cn } from '../lib/utils'
import { Icon } from './icon'

export function Navbar({ route, onUpload }) {
  const isLanding = route === 'landing'
  const [activeSession, setActiveSession] = useState(() => {
    return typeof window !== 'undefined' ? localStorage.getItem('argus_active_session') : null
  })
  const [datasetMenu, setDatasetMenu] = useState(false)
  const menuRef = useRef(null)

  // Listen for storage changes or route changes to keep activeSession fresh
  useEffect(() => {
    const update = () => {
      if (typeof window !== 'undefined') {
        setActiveSession(localStorage.getItem('argus_active_session'))
      }
    }
    window.addEventListener('popstate', update)
    return () => window.removeEventListener('popstate', update)
  }, [route])

  // Close dataset menu on outside click
  useEffect(() => {
    if (!datasetMenu) return
    const handleClick = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setDatasetMenu(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [datasetMenu])

  const datasets = useApi(() => api.datasets(), [])
  const activeDatasetId = typeof window !== 'undefined' ? localStorage.getItem('argus_active_dataset') : null
  const currentDataset = datasets.data?.find((d) => d._id === activeDatasetId) || datasets.data?.[0]

  const dashboardTo = activeSession ? `/dashboard/${activeSession}` : '/dashboard'

  const navItems = [
    { key: 'dashboard', label: 'Chat / Dashboard', to: dashboardTo, icon: 'chat', match: ['dashboard'] },
    { key: 'history', label: 'History', to: '/history', icon: 'clock', match: ['history'] },
    { key: 'analytics', label: 'Analytics', to: '/analytics', icon: 'barChart', match: ['analytics'] },
  ]

  return (
    <header className={cn('sticky top-0 z-50 border-b border-border/80', isLanding ? 'bg-noir/80 backdrop-blur-md' : 'bg-noir/95 backdrop-blur-sm')}>
      <div className="mx-auto flex max-w-[1440px] items-center gap-6 px-6 py-2.5 sm:px-8 lg:px-12">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 no-underline">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-cherry/20 text-cherry border border-cherry/30">
            <Icon name="shield" size={20} strokeWidth={2} />
          </div>
          <span className="font-display text-[26px] font-semibold leading-none text-cotton tracking-tight">Argus</span>
        </Link>

        {/* Nav tabs */}
        <nav aria-label="Main" className="ml-4 hidden items-center gap-1.5 sm:flex">
          {navItems.map((item) => {
            const active = (item.match ?? [item.key]).includes(route)
            return (
              <Link
                key={item.key}
                to={item.to}
                className={cn(
                  'flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium no-underline transition-all',
                  active ? 'bg-active text-cotton shadow-sm border border-border' : 'text-muted hover:bg-hover hover:text-cotton',
                )}
              >
                <Icon name={item.icon} size={15} strokeWidth={1.8} />
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Dataset Switcher Tab (persisted) */}
        {datasets.data && datasets.data.length > 0 && (
          <div className="relative ml-2 hidden md:block" ref={menuRef}>
            <button
              type="button"
              onClick={() => setDatasetMenu((o) => !o)}
              className="flex items-center gap-2 rounded-xl border border-line-strong bg-hover/60 px-3 py-1.5 text-xs font-medium text-soft hover:border-cotton/40 hover:text-cotton transition-colors cursor-pointer"
            >
              <Icon name="database" size={13} className="text-ok" />
              <span className="max-w-[160px] truncate">{currentDataset?.name || 'Datasets'}</span>
              <span className="rounded bg-line px-1.5 py-0.5 text-[10px] text-faint">
                {currentDataset?.document_count || 0} docs
              </span>
              <Icon name="chevronDown" size={12} className={cn('transition-transform text-faint', datasetMenu && 'rotate-180')} />
            </button>

            {datasetMenu && (
              <div className="absolute left-0 top-10 z-50 w-72 rounded-xl border border-border bg-card p-2 shadow-2xl">
                <div className="px-3 py-2 text-[11px] font-semibold text-faint uppercase tracking-wider">
                  Select Dataset / Workspace
                </div>
                <div className="flex flex-col gap-1 max-h-60 overflow-y-auto">
                  {datasets.data.map((ds) => {
                    const isSelected = ds._id === (currentDataset?._id)
                    return (
                      <button
                        key={ds._id}
                        type="button"
                        onClick={async () => {
                          setDatasetMenu(false)
                          await startChat(ds._id)
                        }}
                        className={cn(
                          'flex items-center justify-between rounded-lg px-3 py-2 text-left text-xs transition-colors cursor-pointer',
                          isSelected ? 'bg-active text-cotton font-medium' : 'text-soft hover:bg-hover hover:text-cotton'
                        )}
                      >
                        <div className="min-w-0 flex-1 pr-2">
                          <p className="m-0 truncate font-medium text-cotton">{ds.name}</p>
                          <p className="m-0 text-[10px] text-muted">{ds.document_count} documents · {ds.page_count} pages</p>
                        </div>
                        {isSelected && <Icon name="check" size={14} className="text-ok flex-none" />}
                      </button>
                    )
                  })}
                </div>
                <div className="mt-1 border-t border-border pt-1">
                  <button
                    type="button"
                    onClick={() => { setDatasetMenu(false); onUpload(); }}
                    className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs text-cherry hover:bg-hover transition-colors cursor-pointer"
                  >
                    <Icon name="upload" size={13} />
                    <span>Upload New Dataset...</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Right CTA cluster */}
        <div className="ml-auto flex items-center gap-3">
          <HelpButton />
          <button
            type="button"
            onClick={onUpload}
            className="inline-flex cursor-pointer items-center gap-2 rounded-xl bg-cherry px-4 py-2 text-sm font-semibold text-cotton shadow-sm transition-all hover:bg-maroon hover:shadow-md"
          >
            <Icon name="upload" size={15} strokeWidth={2} />
            <span className="hidden sm:inline">Upload Files</span>
          </button>
        </div>
      </div>
    </header>
  )
}

export function HelpButton({ topic, className }) {
  const [open, setOpen] = useState(false)
  return (
    <span className={cn('relative inline-flex', className)}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        aria-label={topic ? `Help: ${topic}` : 'Help'}
        className="grid h-8 w-8 cursor-pointer place-items-center rounded-full border border-line-strong text-muted transition-colors hover:border-muted hover:text-cotton"
      >
        <Icon name="help" size={16} strokeWidth={1.8} />
      </button>
      {open && (
        <div className="absolute top-10 right-0 z-50 w-72 rounded-[var(--radius-md)] border border-line-strong bg-raised px-4 py-3 text-sm text-soft shadow-lg">
          {topic || 'Argus verifies every answer against source documents using Natural Language Inference. Upload PDFs or Word files, ask questions, and see evidence-backed results.'}
        </div>
      )}
    </span>
  )
}
