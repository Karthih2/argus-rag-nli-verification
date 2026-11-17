/** Unknown address. */
import { TopBar } from '../components/TopBar'
import { Button } from '../components/ui/button'
import { Display } from '../components/ui/misc'

export default function NotFound() {
  return (
    <>
      <TopBar />
      <main className="mx-auto flex max-w-[1280px] flex-col items-start gap-5 px-8 pt-24 pb-40">
        <Display as="h1" className="text-[56px]">Nothing at this address</Display>
        <p className="m-0 text-lg text-muted">The page may have moved, or the chat was deleted with its dataset.</p>
        <div className="flex gap-3"><Button to="/">Go to the start</Button><Button variant="outline" to="/datasets">See datasets</Button></div>
      </main>
    </>
  )
}
