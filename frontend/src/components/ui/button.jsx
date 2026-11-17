import { cva } from '../../lib/utils'
import { Link } from '../../lib/router'

export const buttonVariants = cva(
  'inline-flex items-center justify-center gap-2 font-medium whitespace-nowrap transition-colors disabled:pointer-events-none disabled:opacity-50 cursor-pointer',
  {
    variants: {
      variant: {
        default: 'bg-primary text-primary-foreground hover:bg-maroon',
        outline: 'border border-line-bright bg-transparent text-cotton hover:border-cotton',
        secondary: 'bg-hover text-cotton border border-line-strong hover:bg-active',
        ghost: 'text-soft hover:bg-hover hover:text-cotton',
        link: 'text-soft underline-offset-4 hover:underline hover:text-cotton',
      },
      size: {
        sm: 'h-9 px-3 text-sm rounded-[var(--radius-sm)]',
        default: 'h-11 px-5 text-[15px] rounded-[var(--radius-md)]',
        lg: 'h-13 px-7 text-base rounded-[var(--radius-md)]',
        icon: 'h-9 w-9 rounded-[var(--radius-sm)]',
      },
    },
    defaultVariants: { variant: 'default', size: 'default' },
  },
)

/** shadcn Button. Pass `to` to render a router link styled as a button. */
export function Button({ variant, size, className, to, ...props }) {
  const classes = buttonVariants({ variant, size, className })
  if (to) return <Link to={to} className={classes} data-slot="button" {...props} />
  return <button type="button" className={classes} data-slot="button" {...props} />
}
