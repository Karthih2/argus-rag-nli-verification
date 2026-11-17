/** Small shadcn primitives: Progress, Skeleton, Separator, Textarea, Alert, Spinner. */
import { cn } from '../../lib/utils'
import { Icon } from '../icon'

export function Progress({ value, className, tone = 'busy' }) {
  const bar = tone === 'ok' ? 'bg-ok-line' : tone === 'warn' ? 'bg-warn' : 'bg-cotton'
  return (
    <div role="progressbar" aria-valuenow={Math.round(value * 100)} aria-valuemin={0} aria-valuemax={100} className={cn('h-1 overflow-hidden rounded-full bg-line', className)}>
      <div className={cn('h-full rounded-full transition-[width] duration-500', bar)} style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%` }} />
    </div>
  )
}

export function Skeleton({ className }) {
  return <div aria-hidden="true" className={cn('anim-shimmer rounded-md bg-line', className)} />
}

export function Separator({ className }) {
  return <div role="separator" className={cn('h-px w-full bg-border', className)} />
}

import { forwardRef } from 'react'

export const Textarea = forwardRef(function Textarea({ className, ...props }, ref) {
  return <textarea ref={ref} className={cn('w-full resize-none border-0 bg-transparent text-base leading-relaxed text-cotton outline-none placeholder:text-faint', className)} {...props} />
})

export function Alert({ tone = 'muted', title, children, className }) {
  const tones = { muted: 'border-line-strong bg-panel', bad: 'border-[#4a1a16] bg-[#241514]', warn: 'border-[#5e4a1e] bg-[#221d14]' }
  return (
    <div role="alert" className={cn('rounded-[var(--radius-md)] border px-5 py-4 text-sm', tones[tone], className)}>
      {title && <p className="m-0 mb-1 font-semibold text-cotton">{title}</p>}
      <div className="text-soft">{children}</div>
    </div>
  )
}

export function Spinner({ size = 16, className }) {
  return <Icon name="spinner" size={size} strokeWidth={2.4} className={cn('anim-spin', className)} />
}

/** Section heading in the display face. */
export function Display({ as: Tag = 'h2', className, ...props }) {
  return <Tag className={cn('m-0 font-display font-semibold leading-[1.05]', className)} {...props} />
}
