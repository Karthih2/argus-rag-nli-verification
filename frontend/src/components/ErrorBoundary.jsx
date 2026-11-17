/** Catches a render error in one page and shows it, instead of unmounting the whole app. */
import { Component } from 'react'
import { Button } from './ui/button'

export class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Page crashed:', error, info.componentStack)
  }

  render() {
    if (!this.state.error) return this.props.children
    return (
      <main role="alert" className="mx-auto flex max-w-[960px] flex-col items-start gap-4 px-8 pt-24">
        <h1 className="m-0 font-display text-5xl font-semibold">This page hit an error</h1>
        <p className="m-0 text-muted">The rest of Argus still works. Details are in the browser console.</p>
        <pre className="m-0 max-w-full overflow-x-auto rounded-[10px] border border-border bg-card p-4 font-mono text-sm text-[#e0857c]">{String(this.state.error)}</pre>
        <Button onClick={() => this.setState({ error: null })}>Try again</Button>
      </main>
    )
  }
}
