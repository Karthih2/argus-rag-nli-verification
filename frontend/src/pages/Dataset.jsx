/** One dataset: totals, documents with live processing, extraction report, chats. */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { useApi } from '../api/hooks'
import { Icon } from '../components/icon'
import { PageState, TopBar } from '../components/TopBar'
import { Badge } from '../components/ui/badge'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card'
import { Display, Progress, Spinner } from '../components/ui/misc'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table'
import { Tabs } from '../components/ui/tabs'
import { UploadDialog } from '../components/upload'
import { startChat } from '../lib/chat'
import { plural, timeAgo } from '../lib/format'
import { Link } from '../lib/router'
import { cn } from '../lib/utils'

const BUSY = ['queued', 'parsing', 'embedding', 'indexing']
const STATUS = { queued: 'Queued', parsing: 'Reading pages', embedding: 'Extracting and embedding', indexing: 'Indexing for search' }
const STEP = { queued: 0.08, parsing: 0.35, embedding: 0.65, indexing: 0.9 }
const PAGE_COLOR = { text: '#3A3734', table: '#EDEBDD', chart: '#B9892A', photo: '#B9892A' }

function StatStrip({ ds }) {
  const cells = [['Documents', ds.document_count], ['Pages', ds.page_count], ['Tables', ds.table_count], ['Charts and photos', ds.image_count], ['Chats', ds.chat_count]]
  return (
    <dl className="m-0 mt-10 grid grid-cols-[repeat(auto-fit,minmax(170px,1fr))] gap-px overflow-hidden rounded-[14px] border border-border bg-border">
      {cells.map(([k, v]) => (
        <div key={k} className="bg-card px-6 py-5">
          <dt className="text-[13px] text-muted">{k}</dt>
          <dd className="m-0 mt-1.5 text-3xl font-semibold tabular">{v}</dd>
        </div>
      ))}
    </dl>
  )
}

function Status({ doc }) {
  const s = doc.processing.status
  if (s === 'ready') return <Badge variant="ok">Ready</Badge>
  if (s === 'failed') return <span className="flex flex-col gap-1"><Badge variant="bad">Failed</Badge><span className="text-xs text-[#e0857c]">{doc.processing.error}</span></span>
  return (
    <span className="flex min-w-[150px] flex-col gap-1.5">
      <span className="flex items-center gap-2 text-[13px] whitespace-nowrap"><Spinner size={12} />{STATUS[s] ?? s}</span>
      <Progress value={STEP[s] ?? 0.1} />
    </span>
  )
}

function PageMap({ doc }) {
  const pages = doc.pages ?? []
  const counts = pages.reduce((m, p) => ({ ...m, [p.kind]: (m[p.kind] || 0) + 1 }), {})
  const empty = new Set(doc.stats?.empty_pages ?? [])
  return (
    <Card>
      <CardHeader>
        <CardTitle className="font-display text-[30px]">Extraction report: {doc.metadata?.title || doc.file.name}</CardTitle>
        <CardDescription>Each square is a page. Check that tables and the contents page were recognised before you rely on answers.</CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        {pages.length === 0 ? <p className="m-0 text-sm text-muted">The report appears when processing finishes.</p> : (
          <div className="grid grid-cols-[repeat(auto-fill,minmax(22px,1fr))] gap-[5px]" aria-label={`${pages.length} pages by kind`}>
            {pages.map((p) => (
              <span key={p.n} title={`Page ${p.n}: ${p.kind}, ${plural(p.chunks, 'chunk')}`}
                className={cn('aspect-[3/4] rounded-[3px]', (p.kind === 'toc' || p.kind === 'blank') && 'border border-dashed border-line-bright', empty.has(p.n) && 'outline-2 outline-offset-1 outline-cherry')}
                style={{ background: PAGE_COLOR[p.kind] ?? 'transparent' }} />
            ))}
          </div>
        )}
        <ul className="m-0 flex list-none flex-wrap gap-5 p-0 text-[13px] text-soft">
          {[['text', 'Text'], ['table', 'Table'], ['chart', 'Chart or photo']].map(([k, label]) => (
            <li key={k} className="flex items-center gap-2"><span className="h-3 w-3 rounded-[3px]" style={{ background: PAGE_COLOR[k] }} />{label}, {(counts[k] || 0) + (k === 'chart' ? counts.photo || 0 : 0)}</li>
          ))}
          <li className="flex items-center gap-2"><span className="h-3 w-3 rounded-[3px] border border-dashed border-line-bright" />Contents or blank, not searched, {(counts.toc || 0) + (counts.blank || 0)}</li>
          {empty.size > 0 && <li className="flex items-center gap-2"><span className="h-3 w-3 rounded-[3px] outline-2 outline-cherry" />No text extracted, {empty.size}</li>}
        </ul>
        {doc.stats?.chunks != null && (
          <p className="m-0 text-sm text-muted">
            {plural(doc.stats.chunks, 'searchable chunk')}, {plural(doc.stats.tables, 'table')}, {plural(doc.stats.charts, 'chart')}, {plural(doc.stats.photos ?? 0, 'photo')}, {plural(doc.stats.quotes, 'quotation')}.
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function Documents({ ds, docs, onChanged }) {
  const [selected, setSelected] = useState(null)
  const doc = docs.find((d) => d._id === selected) ?? docs.find((d) => d.processing.status === 'ready') ?? docs[0]
  async function remove(d) {
    if (!window.confirm(`Delete ${d.file.name}? Its chunks go with it.`)) return
    await api.deleteDocument(d._id)
    onChanged()
  }
  if (!docs.length) return <p className="text-muted">No documents yet. Upload files to start.</p>
  return (
    <div className="flex flex-col gap-6">
      <Card className="overflow-hidden">
        <Table className="min-w-[640px]">
          <TableHeader><TableRow>
            <TableHead className="px-5">Document</TableHead><TableHead className="text-right">Pages</TableHead><TableHead className="text-right">Chunks</TableHead>
            <TableHead className="text-right">Tables</TableHead><TableHead className="text-right">Images</TableHead><TableHead>Status</TableHead><TableHead><span className="sr-only">Actions</span></TableHead>
          </TableRow></TableHeader>
          <TableBody>
            {docs.map((d) => (
              <TableRow key={d._id} onClick={() => setSelected(d._id)} className={cn('cursor-pointer hover:bg-[#232121]', d._id === doc?._id && 'bg-[#232121]')}>
                <TableCell className="px-5"><span className="block font-medium">{d.metadata?.title || d.file.name}</span><span className="text-[13px] text-faint">{d.file.name}</span></TableCell>
                <TableCell className="text-right tabular">{d.metadata?.page_count ?? '—'}</TableCell>
                <TableCell className="text-right tabular">{d.stats?.chunks ?? '—'}</TableCell>
                <TableCell className="text-right tabular">{d.stats?.tables ?? '—'}</TableCell>
                <TableCell className="text-right tabular">{d.stats?.chunks != null ? (d.stats.charts || 0) + (d.stats.photos || 0) : '—'}</TableCell>
                <TableCell><Status doc={d} /></TableCell>
                <TableCell className="text-right">
                  {!ds.read_only && ['ready', 'failed'].includes(d.processing.status) && (
                    <Button variant="ghost" size="icon" aria-label={`Delete ${d.file.name}`} onClick={(e) => { e.stopPropagation(); remove(d) }}><Icon name="trash" size={16} /></Button>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Card>
      {doc && <PageMap doc={doc} />}
    </div>
  )
}

function Chats({ sessions }) {
  if (!sessions.length) return <p className="text-muted">No chats yet. Start one from the button above.</p>
  return (
    <Card className="overflow-hidden">
      <Table>
        <TableHeader><TableRow><TableHead className="px-5">Chat</TableHead><TableHead className="text-right">Questions</TableHead><TableHead className="text-right">Verified</TableHead><TableHead className="text-right">Withheld</TableHead><TableHead className="text-right">Avg trust</TableHead><TableHead>Updated</TableHead></TableRow></TableHeader>
        <TableBody>
          {sessions.map((s) => (
            <TableRow key={s._id} className="hover:bg-[#232121]">
              <TableCell className="px-5"><Link to={`/chat/${s._id}`} className="font-medium text-cotton">{s.title || 'Untitled chat'}</Link></TableCell>
              <TableCell className="text-right tabular">{s.turns}</TableCell>
              <TableCell className="text-right tabular">{s.summary?.ACCEPT ?? 0}</TableCell>
              <TableCell className="text-right tabular">{s.summary?.BLOCK ?? 0}</TableCell>
              <TableCell className="text-right tabular">{s.turns ? s.summary?.avg_trust : '—'}</TableCell>
              <TableCell className="text-muted">{timeAgo(s.updated_at)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}

export default function Dataset({ params }) {
  const id = params.id
  const [tab, setTab] = useState('documents')
  const [uploadOpen, setUploadOpen] = useState(false)
  const [starting, setStarting] = useState(false)
  const docs = useApi(() => api.documents(id), [id])
  const busy = docs.data?.some((d) => BUSY.includes(d.processing.status))
  const ds = useApi(() => api.dataset(id), [id], { poll: busy ? 4000 : 0 })
  const sessions = useApi(() => api.sessions(id), [id])

  useEffect(() => {
    if (!busy) return undefined
    const t = setInterval(docs.reload, 3000)
    return () => clearInterval(t)
  }, [busy, docs.reload])

  const ready = (docs.data ?? []).filter((d) => d.processing.status === 'ready').map((d) => d._id)
  async function chat(question = '') {
    setStarting(true)
    await startChat(id, ready.length === docs.data?.length ? [] : ready, question).finally(() => setStarting(false))
  }

  return (
    <>
      <TopBar crumbs={[{ label: 'Datasets', to: '/datasets' }, { label: ds.data?.name ?? '' }]} />
      <main className="mx-auto max-w-[1280px] px-8 pt-12 pb-40">
        <PageState loading={ds.loading && !ds.data} error={ds.error}>
          {ds.data && (
            <>
              <div className="flex flex-wrap items-end justify-between gap-6">
                <div className="flex flex-col gap-3">
                  <Display as="h1" className="text-[56px] leading-none">{ds.data.name}</Display>
                  {ds.data.description && <p className="m-0 max-w-[60ch] text-[17px] text-muted">{ds.data.description}</p>}
                  <span className="flex flex-wrap gap-2">
                    {ds.data.read_only && <Badge>Demo, read-only</Badge>}
                  </span>
                </div>
                <div className="flex flex-wrap gap-3">
                  {!ds.data.read_only && <Button variant="outline" onClick={() => setUploadOpen(true)}><Icon name="upload" size={16} />Upload documents</Button>}
                  <Button onClick={() => chat()} disabled={!ready.length || starting}>{starting ? <Spinner /> : <Icon name="chat" size={16} />}Start a chat</Button>
                </div>
              </div>
              <StatStrip ds={ds.data} />
              <Tabs className="mt-10" label="Dataset sections" value={tab} onValueChange={setTab}
                items={[{ value: 'documents', label: 'Documents' }, { value: 'chats', label: `Chats (${sessions.data?.length ?? 0})` }]} />
              <div className="mt-5 flex flex-wrap items-start gap-6">
                <div className="flex min-w-0 flex-[999_1_640px] flex-col gap-6">
                  {tab === 'documents' && <Documents ds={ds.data} docs={docs.data ?? []} onChanged={() => { docs.reload(); ds.reload() }} />}
                  {tab === 'chats' && <Chats sessions={sessions.data ?? []} />}
                </div>
                <aside className="flex flex-[1_1_320px] flex-col gap-6">
                  {sessions.data?.length > 0 && tab !== 'chats' && (
                    <Card>
                      <CardHeader><CardTitle>Recent chats</CardTitle></CardHeader>
                      <CardContent className="flex flex-col gap-1 pt-3">
                        {sessions.data.slice(0, 4).map((s) => (
                          <Link key={s._id} to={`/chat/${s._id}`} className="flex justify-between gap-3 rounded-[8px] px-3 py-2.5 text-sm text-soft no-underline hover:bg-hover hover:text-cotton">
                            <span className="truncate">{s.title || 'Untitled chat'}</span><span className="flex-none text-faint">{plural(s.turns, 'question')}</span>
                          </Link>
                        ))}
                      </CardContent>
                    </Card>
                  )}
                </aside>
              </div>
            </>
          )}
        </PageState>
      </main>
      {ds.data && <UploadDialog open={uploadOpen} onClose={() => { setUploadOpen(false); docs.reload() }} datasetId={id} datasetName={ds.data.name} />}
    </>
  )
}
