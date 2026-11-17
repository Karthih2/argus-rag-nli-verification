import { cn } from '../../lib/utils'

export function Table({ className, ...props }) {
  return (
    <div data-slot="table-container" className="w-full overflow-x-auto">
      <table data-slot="table" className={cn('w-full border-collapse text-[15px]', className)} {...props} />
    </div>
  )
}
export const TableHeader = (p) => <thead data-slot="table-header" {...p} />
export const TableBody = (p) => <tbody data-slot="table-body" {...p} />
export function TableRow({ className, ...props }) {
  return <tr data-slot="table-row" className={cn('border-b border-hover transition-colors last:border-0', className)} {...props} />
}
export function TableHead({ className, ...props }) {
  return <th data-slot="table-head" className={cn('border-b border-border px-4 py-3 text-left text-[13px] font-medium text-muted', className)} {...props} />
}
export function TableCell({ className, ...props }) {
  return <td data-slot="table-cell" className={cn('px-4 py-3.5 align-middle', className)} {...props} />
}
