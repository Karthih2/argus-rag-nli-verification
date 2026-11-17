/** Upload page: user uploads 4-5 PDF/Word documents, then goes to processing. */
import { useRef, useState } from 'react'
import { api } from '../api/client'
import { Icon } from '../components/icon'
import { HelpButton } from '../components/Navbar'
import { Button } from '../components/ui/button'
import { Display, Spinner } from '../components/ui/misc'
import { navigate } from '../lib/router'
import { cn } from '../lib/utils'

const MAX_MB = 50
const MIN_FILES = 1
const MAX_FILES = 5
const ALLOWED_EXT = ['.pdf', '.doc', '.docx']
const ACCEPT = 'application/pdf,.doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document'

function validateExt(name) {
  return ALLOWED_EXT.some((ext) => name.toLowerCase().endsWith(ext))
}

function fileIcon(name) {
  if (name.toLowerCase().endsWith('.pdf')) return 'file'
  return 'file'
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function Upload() {
  const input = useRef(null)
  const [files, setFiles] = useState([])
  const [over, setOver] = useState(false)
  const [error, setError] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [datasetName, setDatasetName] = useState('')

  function addFiles(fileList) {
    const valid = [...fileList].filter((f) => validateExt(f.name))
    if (!valid.length) { setError('Only PDF and Word files are accepted.'); return }
    setFiles((prev) => {
      const combined = [...prev, ...valid]
      if (combined.length > MAX_FILES) {
        setError(`Maximum ${MAX_FILES} files allowed. Remove some first.`)
        return prev
      }
      setError(null)
      return combined
    })
  }

  function removeFile(index) {
    setFiles((prev) => prev.filter((_, i) => i !== index))
    setError(null)
  }

  async function handleUpload() {
    if (files.length < MIN_FILES) { setError(`Upload at least ${MIN_FILES} document.`); return }
    const big = files.find((f) => f.size > MAX_MB * 1024 * 1024)
    if (big) { setError(`${big.name} exceeds ${MAX_MB} MB limit.`); return }

    setUploading(true)
    setError(null)
    try {
      const name = datasetName.trim() || files[0].name.replace(/\.(pdf|docx?|doc)$/i, '').replace(/[_-]+/g, ' ')
      const ds = await api.createDataset(name)
      await api.upload(ds._id, files)
      navigate(`/processing/${ds._id}`)
    } catch (e) {
      setError(e.message)
      setUploading(false)
    }
  }

  return (
    <main className="mx-auto max-w-[900px] px-6 pt-12 pb-28 sm:px-8">
      {/* Header */}
      <div className="mb-10 flex items-start justify-between gap-4">
        <div>
          <Display as="h1" className="text-[48px] sm:text-[56px]">Upload Documents</Display>
          <p className="mt-3 mb-0 text-lg text-muted">
            Add up to {MAX_FILES} PDF or Word files. Argus will parse, embed, and index them for verified Q&A.
          </p>
        </div>
        <HelpButton topic="Upload between 1 and 5 documents in PDF or Word format (max 50 MB each, 500 pages). After uploading, documents are automatically processed — parsed for text, tables, and images, then embedded and indexed for search." />
      </div>

      {/* Dataset name */}
      <div className="mb-8">
        <label className="mb-2 block text-sm font-medium text-soft">Dataset name <span className="text-faint">(optional)</span></label>
        <input
          type="text"
          value={datasetName}
          onChange={(e) => setDatasetName(e.target.value)}
          placeholder="Auto-generated from first file name"
          className="h-12 w-full rounded-[var(--radius-md)] border border-line-strong bg-card px-4 text-base text-cotton outline-none placeholder:text-faint focus:border-muted"
        />
      </div>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true) }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => { e.preventDefault(); setOver(false); addFiles(e.dataTransfer.files) }}
        className={cn(
          'flex flex-col items-center gap-5 rounded-[var(--radius-xl)] border-[2px] border-dashed px-8 py-14 text-center transition-colors',
          over ? 'border-cotton bg-hover' : 'border-line-bright bg-[#1c1a1a]',
        )}
      >
        <div className="grid h-16 w-16 place-items-center rounded-2xl border border-line-strong bg-hover text-muted">
          <Icon name="upload" size={28} strokeWidth={1.5} />
        </div>
        <div>
          <p className="m-0 text-xl font-semibold text-cotton">Drop files here</p>
          <p className="m-0 mt-1 text-sm text-muted">or click to browse</p>
        </div>
        <input ref={input} type="file" accept={ACCEPT} multiple hidden onChange={(e) => { addFiles(e.target.files); e.target.value = '' }} />
        <Button variant="outline" onClick={() => input.current.click()}>
          <Icon name="file" size={16} />Choose files
        </Button>
        <p className="m-0 text-xs text-faint">PDF or Word · Max {MAX_MB} MB per file · Up to {MAX_FILES} files</p>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="mt-8">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="m-0 text-lg font-semibold">{files.length} of {MAX_FILES} files</h3>
            <span className="text-sm text-muted">{formatSize(files.reduce((s, f) => s + f.size, 0))} total</span>
          </div>
          <ul className="m-0 flex list-none flex-col gap-2 p-0">
            {files.map((f, i) => (
              <li key={`${f.name}-${i}`} className="flex items-center gap-4 rounded-[var(--radius-md)] border border-border bg-card px-5 py-4">
                <div className="grid h-10 w-10 flex-none place-items-center rounded-lg bg-hover text-muted">
                  <Icon name={fileIcon(f.name)} size={20} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="m-0 truncate text-[15px] font-medium text-cotton">{f.name}</p>
                  <p className="m-0 text-xs text-faint">{formatSize(f.size)} · {f.name.split('.').pop().toUpperCase()}</p>
                </div>
                <button
                  type="button"
                  onClick={() => removeFile(i)}
                  disabled={uploading}
                  aria-label={`Remove ${f.name}`}
                  className="grid h-8 w-8 cursor-pointer place-items-center rounded-md text-faint transition-colors hover:bg-hover hover:text-cotton"
                >
                  <Icon name="x" size={16} />
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Error */}
      {error && <p role="alert" className="mt-4 mb-0 text-sm text-[#e0857c]"><Icon name="alert" size={14} className="mr-1 inline" />{error}</p>}

      {/* Upload button */}
      <div className="mt-10 flex items-center gap-4">
        <Button size="lg" disabled={!files.length || uploading} onClick={handleUpload}>
          {uploading ? <Spinner /> : <Icon name="upload" />}
          {uploading ? 'Uploading…' : `Upload ${files.length ? `${files.length} file${files.length > 1 ? 's' : ''}` : 'documents'}`}
        </Button>
        <Button variant="outline" size="lg" onClick={() => navigate('/')}>Cancel</Button>
      </div>
    </main>
  )
}
