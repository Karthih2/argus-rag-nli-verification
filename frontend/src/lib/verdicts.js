/** One source of truth for how decisions and claim labels look and read. */

export const DECISIONS = {
  ACCEPT: { label: 'Verified', banner: 'Verified against the source', icon: 'checkCircle', tone: 'ok' },
  ACCEPT_LOW_CONFIDENCE: { label: 'Partly verified', banner: 'Partly verified', icon: 'alert', tone: 'warn' },
  WARN: { label: 'Some statements not found', banner: 'Some statements were not found in the source', icon: 'alert', tone: 'warn' },
  BLOCK: { label: 'Withheld', banner: 'Answer withheld: it conflicted with the source', icon: 'ban', tone: 'bad' },
  NO_SUPPORT: { label: 'Not in documents', banner: 'Not in these documents', icon: 'search', tone: 'muted' },
}

export const DECISION_ORDER = ['ACCEPT', 'ACCEPT_LOW_CONFIDENCE', 'WARN', 'BLOCK', 'NO_SUPPORT']

/** Banner / pill colours per tone (text always paired with an icon and a word). */
export const TONE = {
  ok: 'bg-ok-bg text-ok-ink border-[#bfcbb0]',
  warn: 'bg-warn-bg text-warn-ink border-[#dcc28a]',
  bad: 'bg-cherry text-cotton border-maroon',
  muted: 'bg-hover text-soft border-line-strong',
}

/** Chart colours per decision, distinct in lightness as well as hue. */
export const DECISION_COLOR = {
  ACCEPT: '#8DB87A',
  ACCEPT_LOW_CONFIDENCE: '#C9973A',
  WARN: '#E2CF9E',
  BLOCK: '#B23A30',
  NO_SUPPORT: '#57534C',
}

export const CLAIMS = {
  SUPPORTED: { label: 'Supported', underline: '#3F7A4F', dashed: false },
  WEAKLY_SUPPORTED: { label: 'Weak', underline: '#C9973A', dashed: true },
  UNVERIFIED: { label: 'Not found', underline: '#8A867A', dashed: true },
  CONTRADICTED: { label: 'Contradicted', underline: '#B23A30', dashed: false },
}

/** Trust-score bands: the one place that decides how a trust number is coloured. */
export const TRUST_BANDS = [
  { min: 80, label: '80+', tone: 'ok', color: '#8DB87A', text: 'text-ok' },
  { min: 50, label: '50–79', tone: 'warn', color: '#C9973A', text: 'text-warn' },
  { min: 0, label: 'Below 50', tone: 'bad', color: '#57534C', text: 'text-[#e0857c]' },
]
export const trustBand = (trust) => (trust == null ? null : TRUST_BANDS.find((b) => trust >= b.min))

/** Mean NLI split of an answer, from score_card.nli (older answers: rebuilt from their claims). */
export function nliSplit(result) {
  const nli = result?.score_card?.nli
  if (nli) return nli
  const claims = result?.claims ?? []
  if (!claims.length) return null
  const mean = (f) => claims.reduce((s, c) => s + f(c), 0) / claims.length
  return {
    entailment: mean((c) => c.scores?.entailment ?? c.support ?? 0),
    neutral: mean((c) => c.scores?.neutral ?? c.neutral ?? 0),
    contradiction: mean((c) => c.scores?.contradiction ?? c.contra ?? 0),
  }
}

/** One claim's NLI split from its best-supporting premise (older answers: closest fields). */
export const claimSplit = (c) => c.scores ?? { entailment: c.support ?? 0, neutral: c.neutral ?? 0, contradiction: c.contra ?? 0 }
