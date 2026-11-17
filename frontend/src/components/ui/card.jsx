import { cn } from '../../lib/utils'

export function Card({ className, ...props }) {
  return <div data-slot="card" className={cn('rounded-[var(--radius-lg)] border border-border bg-card', className)} {...props} />
}
export function CardHeader({ className, ...props }) {
  return <div data-slot="card-header" className={cn('flex flex-col gap-1.5 px-6 pt-6', className)} {...props} />
}
export function CardTitle({ className, as: Tag = 'h2', ...props }) {
  return <Tag data-slot="card-title" className={cn('m-0 text-[17px] font-semibold', className)} {...props} />
}
export function CardDescription({ className, ...props }) {
  return <p data-slot="card-description" className={cn('m-0 text-sm text-muted-foreground', className)} {...props} />
}
export function CardContent({ className, ...props }) {
  return <div data-slot="card-content" className={cn('px-6 py-5', className)} {...props} />
}
export function CardFooter({ className, ...props }) {
  return <div data-slot="card-footer" className={cn('flex items-center px-6 pb-6', className)} {...props} />
}
