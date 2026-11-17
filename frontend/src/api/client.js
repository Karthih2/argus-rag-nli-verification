/** Every API call in one place. All requests go to the FastAPI backend under /api. */

const BASE = '/api'

async function request(path, { method = 'GET', body, form } = {}) {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: form ?? (body ? JSON.stringify(body) : undefined),
  })
  const data = await res.json().catch(() => null)
  if (!res.ok) throw new Error(data?.detail || `${res.status} ${res.statusText}`)
  return data
}

export const api = {
  health: () => request('/health'),

  datasets: () => request('/datasets'),
  dataset: (id) => request(`/datasets/${id}`),
  createDataset: (name) => request('/datasets', { method: 'POST', body: { name } }),
  deleteDataset: (id) => request(`/datasets/${id}`, { method: 'DELETE' }),

  documents: (datasetId) => request(`/datasets/${datasetId}/documents`),
  deleteDocument: (id) => request(`/documents/${id}`, { method: 'DELETE' }),
  upload(datasetId, files) {
    const form = new FormData()
    for (const f of files) form.append('files', f)
    return request(`/datasets/${datasetId}/documents`, { method: 'POST', form })
  },

  sessions: (datasetId) => request(datasetId ? `/sessions?dataset_id=${encodeURIComponent(datasetId)}` : '/sessions'),
  session: (id) => request(`/sessions/${id}`),
  deleteSession: (id) => request(`/sessions/${id}`, { method: 'DELETE' }),
  createSession: (datasetId, documentIds) =>
    request('/sessions', { method: 'POST', body: { dataset_id: datasetId, document_ids: documentIds } }),

  queries: ({ datasetId, decision, complete, limit = 20, skip = 0 } = {}) => {
    const q = new URLSearchParams({ limit, skip })
    if (complete) q.set('complete', 'true')
    if (datasetId) q.set('dataset_id', datasetId)
    if (decision) q.set('decision', decision)
    return request(`/queries?${q}`)
  },
  query: (id) => request(`/queries/${id}`),
  feedback: (id, value, reason) => request(`/queries/${id}/feedback`, { method: 'POST', body: { value, reason } }),

  analytics: (datasetId, days) => request(`/analytics?dataset_id=${encodeURIComponent(datasetId)}&days=${days}`),
  trustInfo: () => request('/trust-info'),
}

export const urls = {
  page: (documentId, page, chunkId) =>
    `${BASE}/documents/${documentId}/pages/${page}.png${chunkId ? `?highlight=${chunkId}` : ''}`,
}

/**
 * POST /api/ask and read the Server-Sent Events stream.
 * Calls onStage for progress, then onResult or onError once. Returns an abort function.
 */
export function ask(sessionId, question, { onStage, onResult, onError }) {
  const controller = new AbortController()
  let gotResult = false
  const handlers = {
    stage: onStage,
    result: (d) => { gotResult = true; onResult(d) },
    error: (d) => { gotResult = true; onError(d.error) },
  }
  ;(async () => {
    const res = await fetch(`${BASE}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, question }),
      signal: controller.signal,
    })
    if (!res.ok) throw new Error((await res.json().catch(() => null))?.detail || `Ask failed: ${res.status}`)
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let event = 'message'
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split(/\r?\n/)
      buffer = lines.pop() ?? ''
      for (const line of lines) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) handlers[event]?.(JSON.parse(line.slice(5)))
        else if (line === '') event = 'message'
      }
    }
    if (!gotResult) onError('Connection closed without a result')
  })().catch((err) => {
    if (err.name !== 'AbortError') onError(err.message)
  })
  return () => controller.abort()
}
