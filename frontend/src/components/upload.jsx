/** Upload: a drop zone and a dialog. Uploading creates a private dataset, then opens it. */
import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import { navigate } from '../lib/router'
import { cn } from '../lib/utils'
import { Icon } from './icon'
import { Button } from './ui/button'
import { Spinner } from './ui/misc'

const MAX_MB = 50
const MAX_FILES = 5
const ALLOWED_EXT = ['.pdf', '.doc', '.docx']
const ACCEPT = 'application/pdf,.doc,.docx,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document'

function datasetNameFrom(files) {
  const first = files[0].name.replace(/\.(pdf|docx?|doc)$/i, '').replace(/[_-]+/g, ' ')
  return files.length > 1 ? `${first} and ${files.length - 1} more` : first
}

function validateExt(name) {
  return ALLOWED_EXT.some((ext) => name.toLowerCase().endsWith(ext))
}

/** Validate, create a dataset (unless one is given), upload, and go to it. */
export function useUpload(datasetId, onDone) {
  const [state, setState] = useState({ busy: false, error: null })
  async function upload(fileList) {
    const files = [...fileList].filter((f) => validateExt(f.name))
    if (!files.length) return setState({ busy: false, error: 'Choose PDF or Word files.' })
    if (files.length > MAX_FILES) return setState({ busy: false, error: `Max ${MAX_FILES} files at a time.` })
    const big = files.find((f) => f.size > MAX_MB * 1024 * 1024)
    if (big) return setState({ busy: false, error: `${big.name} is over ${MAX_MB} MB.` })
    setState({ busy: true, error: null })
    try {
      const id = datasetId ?? (await api.createDataset(datasetNameFrom(files)))._id
      await api.upload(id, files)
      setState({ busy: false, error: null })
      onDone?.()
      navigate(`/d/${id}`)
    } catch (e) {
      setState({ busy: false, error: e.message })
    }
  }
  return { ...state, upload }
}

export function DropZone({ datasetId, onDone, className, children }) {
  const input = useRef(null)
  const [over, setOver] = useState(false)
  const { busy, error, upload } = useUpload(datasetId, onDone)
  return (
    <div
      onDragOver={(e) => { e.preventDefault(); setOver(true) }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => { e.preventDefault(); setOver(false); upload(e.dataTransfer.files) }}
      className={cn(
        'flex flex-col items-center gap-4 rounded-[var(--radius-xl)] border-[1.5px] border-dashed px-8 py-16 text-center transition-colors',
        over ? 'border-cotton bg-hover' : 'border-line-bright bg-[#1c1a1a]',
        className,
      )}
    >
      {children}
      <input ref={input} type="file" accept={ACCEPT} multiple hidden onChange={(e) => upload(e.target.files)} />
      <Button onClick={() => input.current.click()} disabled={busy}>
        {busy ? <Spinner /> : <Icon name="upload" />}
        {busy ? 'Uploading' : 'Choose files'}
      </Button>
      <p className="m-0 text-sm text-muted">PDF or Word, up to {MAX_MB} MB and 500 pages each. Max {MAX_FILES} files.</p>
      {error && <p role="alert" className="m-0 text-sm text-[#e0857c]">{error}</p>}
    </div>
  )
}

/** Modal upload dialog (native <dialog>, so focus and Escape work without a library). */
export function UploadDialog({ open, onClose, datasetId, datasetName }) {
  const ref = useRef(null)
  useEffect(() => {
    const d = ref.current
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])
  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onClick={(e) => e.target === ref.current && onClose()}
      className="m-auto w-[min(640px,92vw)] rounded-[var(--radius-xl)] border border-line-strong bg-raised p-0 text-cotton backdrop:bg-black/60"
    >
      <div className="flex flex-col gap-5 p-7">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="m-0 font-display text-4xl font-semibold">Upload Documents</h2>
            <p className="mt-2 mb-0 text-[15px] text-muted">
              {datasetId ? `Adds to ${datasetName}. ` : 'Creates a private dataset. '}You can ask as soon as the first document is ready.
            </p>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close"><Icon name="x" /></Button>
        </div>
        <DropZone datasetId={datasetId} onDone={onClose}>
          <Icon name="fileUp" size={40} strokeWidth={1.3} />
          <p className="m-0 text-xl font-semibold">Drop PDF or Word files here</p>
        </DropZone>
      </div>
    </dialog>
  )
}
