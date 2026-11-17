/** Top navigation bar replacing the floating Dock. */
import { useState } from 'react'
import { Link } from '../lib/router'
import { cn } from '../lib/utils'
import { Icon } from './icon'

const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', to: '/dashboard', icon: 'grid', match: ['dashboard'] },
  { key: 'analytics', label: 'Analytics', to: '/analytics', icon: 'barChart', match: ['analytics'] },
]

export function Navbar({ route, onUpload }) {
  const isLanding = route === 'landing'
  return (
    <header className={cn('sticky top-0 z-50 border-b border-border', isLanding ? 'bg-noir/80 backdrop-blur-md' : 'bg-noir')}>
      <div className="mx-auto flex max-w-[1440px] items-center gap-6 px-6 py-3 sm:px-8 lg:px-12">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 no-underline">
          <Icon name="shield" size={24} strokeWidth={1.8} className="text-cherry" />
          <span className="font-display text-[28px] font-semibold leading-none text-cotton">Argus</span>
        </Link>

        {/* Nav links */}
        <nav aria-label="Main" className="ml-4 hidden items-center gap-1 sm:flex">
          {NAV_ITEMS.map((item) => {
            const active = (item.match ?? [item.key]).includes(route)
            return (
              <Link
                key={item.key}
                to={item.to}
                className={cn(
                  'flex items-center gap-2 rounded-[var(--radius-sm)] px-3.5 py-2 text-sm font-medium no-underline transition-colors',
                  active ? 'bg-active text-cotton' : 'text-muted hover:bg-hover hover:text-cotton',
                )}
              >
                <Icon name={item.icon} size={16} strokeWidth={1.6} />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="ml-auto flex items-center gap-3">
          {/* Help */}
          <HelpButton />
          {/* Upload CTA */}
          <button
            type="button"
            onClick={onUpload}
            className="inline-flex cursor-pointer items-center gap-2 rounded-[var(--radius-md)] bg-cherry px-4 py-2.5 text-sm font-medium text-cotton transition-colors hover:bg-maroon"
          >
            <Icon name="upload" size={16} strokeWidth={1.8} />
            <span className="hidden sm:inline">Upload</span>
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
