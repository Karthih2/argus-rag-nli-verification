/** Slim page header: wordmark, breadcrumb, and a right-hand slot. */
import { Link } from '../lib/router'

export function TopBar({ crumbs = [], right }) {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-[1280px] flex-wrap items-center gap-5 px-8 py-4">
        <Link to="/" className="font-display text-[26px] font-semibold text-cotton no-underline">Argus</Link>
        <nav aria-label="Breadcrumb" className="flex flex-wrap items-center gap-2.5 text-sm text-muted">
          {crumbs.map((c, i) => (
            <span key={c.label} className="flex items-center gap-2.5">
              {i > 0 && <span aria-hidden="true">/</span>}
              {c.to ? <Link to={c.to} className="text-muted no-underline hover:text-cotton">{c.label}</Link> : <span className="text-cotton">{c.label}</span>}
            </span>
          ))}
        </nav>
        <div className="ml-auto">{right}</div>
      </div>
    </header>
  )
}

export function PageState({ loading, error, empty, children }) {
  if (error) return <p role="alert" className="mx-auto max-w-[1280px] px-8 py-16 text-[#e0857c]">Could not load: {error.message}</p>
  if (loading) return <p className="mx-auto max-w-[1280px] px-8 py-16 text-muted">Loading</p>
  if (empty) return empty
  return children
}
