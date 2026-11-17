import { cva } from '../../lib/utils'
import { TONE } from '../../lib/verdicts'

const badgeVariants = cva('inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[13px] font-medium whitespace-nowrap', {
  variants: {
    variant: {
      outline: 'border-line-strong text-soft',
      ok: TONE.ok,
      warn: TONE.warn,
      bad: TONE.bad,
      muted: TONE.muted,
    },
  },
  defaultVariants: { variant: 'outline' },
})

export function Badge({ variant, className, ...props }) {
  return <span data-slot="badge" className={badgeVariants({ variant, className })} {...props} />
}
