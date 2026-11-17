import { cn } from '../../lib/utils'

/** Segmented tabs (shadcn TabsList look). Controlled: pass value and onValueChange. */
export function Tabs({ value, onValueChange, items, label, className }) {
  return (
    <div role="tablist" aria-label={label} className={cn('inline-flex gap-1 rounded-[var(--radius-md)] border border-border bg-card p-1', className)}>
      {items.map((it) => (
        <button
          key={it.value}
          type="button"
          role="tab"
          aria-selected={value === it.value}
          disabled={it.disabled}
          onClick={() => onValueChange(it.value)}
          className={cn(
            'cursor-pointer rounded-[7px] px-3.5 py-2 text-[13px] font-medium transition-colors disabled:opacity-40',
            value === it.value ? 'bg-active text-cotton' : 'text-muted hover:text-cotton',
          )}
        >
          {it.label}
        </button>
      ))}
    </div>
  )
}
