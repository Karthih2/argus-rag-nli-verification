/** Start a conversation and open it, optionally asking a first question. */
import { api } from '../api/client'
import { navigate } from './router'

export async function startChat(datasetId, documentIds = [], question = '') {
  const session = await api.createSession(datasetId, documentIds)
  navigate(`/chat/${session._id}${question ? `?q=${encodeURIComponent(question)}` : ''}`)
}

/** The demo dataset: the read-only one if present, else the first. */
export const pickDemo = (datasets = []) => datasets.find((d) => d.read_only) ?? datasets.find((d) => d._id === 'ds_nasa') ?? datasets[0]
