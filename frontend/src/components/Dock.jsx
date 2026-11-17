/** Floating dock: page links, a live status segment, and the upload action. Pinned to the bottom. */
import { useActivity } from '../lib/activity'
import { Link } from '../lib/router'
import { cn } from '../lib/utils'
import { Icon } from './icon'
import { Progress } from './ui/misc'

const ITEMS = [
  { key: 'landing', label: 'Home', to: '/', icon: 'home' },
  { key: 'datasets', label: 'Datasets', to: '/datasets', icon: 'layers', match: ['datasets', 'dataset', 'chat'] },
  { key: 'analytics', label: 'Analytics', to: '/analytics', icon: 'chart' },
]
const DOT = { ok: 'bg-ok', warn: 'bg-warn', busy: 'bg-cotton' }

function DockLink({ item, active }) {
  return (
    <Link
      to={item.to}
      aria-label={item.label}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'group relative grid h-[50px] w-[50px] place-items-center rounded-xl border transition-transform duration-200 hover:-translate-y-2 hover:scale-110',
        active ? 'border-line-bright bg-active text-cotton' : 'border-line-strong bg-hover text-muted hover:text-cotton',
      )}
    >
      <Icon name={item.icon} size={22} strokeWidth={1.6} />
      <span className="pointer-events-none absolute bottom-[64px] left-1/2 -translate-x-1/2 rounded-md bg-cotton px-2 py-1 text-xs font-medium whitespace-nowrap text-noir opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
        {item.label}
      </span>
      <span className={cn('absolute -bottom-2 h-1 w-1 rounded-full', active ? 'bg-cherry' : 'bg-transparent')} />
    </Link>
  )
}

export function Dock({ route, onUpload }) {
  const { live } = useActivity()
  return (
    <div className="pointer-events-none fixed inset-x-0 bottom-5 z-40 flex justify-center px-4">
      <nav aria-label="Main" className="pointer-events-auto flex max-w-full items-center gap-2 rounded-[var(--radius-xl)] border border-line-strong bg-raised px-3 py-2.5 shadow-[0_20px_40px_-12px_rgba(0,0,0,.7)]">
        {ITEMS.map((it) => (
          <DockLink key={it.key} item={it} active={(it.match ?? [it.key]).includes(route)} />
        ))}
        <span aria-hidden="true" className="mx-1.5 h-10 w-px bg-line-strong" />
        <div role="status" aria-live="polite" className="hidden w-[300px] items-center gap-3 px-1.5 sm:flex">
          <span className={cn('h-2 w-2 flex-none rounded-full', DOT[live.tone] ?? 'bg-cotton', live.tone === 'busy' && 'anim-pulse')} />
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <span className="flex justify-between gap-2 text-[13px]">
              <span className="flex-none font-medium">{live.title}</span>
              <span className="truncate text-muted tabular">{live.extra || live.meta}</span>
            </span>
            <Progress value={live.progress} tone={live.tone} />
          </div>
        </div>
        <button
          type="button"
          onClick={onUpload}
          aria-label="Upload documents"
          className="group relative grid h-[54px] w-[54px] cursor-pointer place-items-center rounded-[14px] border border-[#9a1a14] bg-cherry text-cotton transition-transform duration-200 hover:-translate-y-2 hover:scale-110"
        >
          <Icon name="upload" size={24} strokeWidth={1.8} />
          <span className="pointer-events-none absolute bottom-[66px] left-1/2 -translate-x-1/2 rounded-md bg-cotton px-2 py-1 text-xs font-medium whitespace-nowrap text-noir opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100">
            Upload
          </span>
        </button>
      </nav>
    </div>
  )
}
