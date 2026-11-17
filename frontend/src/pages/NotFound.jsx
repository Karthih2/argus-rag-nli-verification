/** Unknown address. */
import { Button } from '../components/ui/button'
import { Display } from '../components/ui/misc'

export default function NotFound() {
  return (
    <main className="mx-auto flex max-w-[1280px] flex-col items-start gap-5 px-8 pt-24 pb-40">
      <Display as="h1" className="text-[56px]">Nothing at this address</Display>
      <p className="m-0 text-lg text-muted">The page may have moved, or the session was deleted.</p>
      <div className="flex gap-3">
        <Button to="/">Go home</Button>
        <Button variant="outline" to="/upload">Upload documents</Button>
      </div>
    </main>
  )
}
