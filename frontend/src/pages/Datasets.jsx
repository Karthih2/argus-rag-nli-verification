/** All datasets, with their size. */
import { api } from '../api/client'
import { useApi } from '../api/hooks'
import { Icon } from '../components/icon'
import { PageState, TopBar } from '../components/TopBar'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Display } from '../components/ui/misc'
import { plural, timeAgo } from '../lib/format'
import { Link } from '../lib/router'

export default function Datasets({ onUpload }) {
  const { data, loading, error, reload } = useApi(() => api.datasets(), [])
  async function remove(ds) {
    if (!window.confirm(`Delete "${ds.name}" and everything in it? This can't be undone.`)) return
    await api.deleteDataset(ds._id)
    reload()
  }
  return (
    <>
      <TopBar crumbs={[{ label: 'Datasets' }]} />
      <main className="mx-auto max-w-[1280px] px-8 pt-12 pb-40">
        <div className="mb-10 flex flex-wrap items-end justify-between gap-6">
          <div>
            <Display as="h1" className="text-[56px] leading-none">Datasets</Display>
            <p className="mt-3 mb-0 text-[17px] text-muted">Each dataset has its own documents and chats.</p>
          </div>
          <Button onClick={onUpload}><Icon name="upload" size={16} />Upload to a new dataset</Button>
        </div>
        <PageState loading={loading} error={error} empty={data?.length === 0 && (
          <p className="text-muted">No datasets yet. Upload documents to create one.</p>
        )}>
          <ul className="m-0 flex list-none flex-col gap-4 p-0">
            {data?.map((ds) => (
              <li key={ds._id} className="flex flex-wrap items-center gap-6 rounded-[14px] border border-border bg-card px-7 py-6 transition-colors hover:border-line-bright">
                <div className="min-w-0 flex-[1_1_320px]">
                  <Link to={`/d/${ds._id}`} className="font-display text-[30px] leading-tight font-semibold text-cotton no-underline hover:text-white">{ds.name}</Link>
                  <p className="m-0 mt-1 text-sm text-muted">
                    {plural(ds.document_count, 'document')}, {plural(ds.page_count, 'page')}, {plural(ds.chat_count, 'chat')}
                    {ds.created_at && `, created ${timeAgo(ds.created_at)}`}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  {ds.read_only && <Badge>Demo, read-only</Badge>}
                  <Button variant="secondary" to={`/d/${ds._id}`}>Open</Button>
                  {!ds.read_only && <Button variant="ghost" size="icon" aria-label={`Delete ${ds.name}`} onClick={() => remove(ds)}><Icon name="trash" size={16} /></Button>}
                </div>
              </li>
            ))}
          </ul>
        </PageState>
      </main>
    </>
  )
}
