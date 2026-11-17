/** Landing: clean hero with Argus branding and pipeline overview. */
import { Icon } from '../components/icon'
import { HelpButton } from '../components/Navbar'
import { Button } from '../components/ui/button'
import { Display } from '../components/ui/misc'
import { GridBackdrop, HeroArt, STEP_ART } from '../features/art'
import { navigate } from '../lib/router'

const STEPS = [
  ['retrieve', 'Retrieve', 'Semantic + keyword search across your documents, reranked to the best passages.'],
  ['draft', 'Draft with quotes', 'The model answers in short claims, each citing a passage and copying the exact words.'],
  ['check', 'Check every claim', 'NLI model tests each claim against its passage. Numbers and quotes must match.'],
  ['decide', 'Decide', 'Supported answers show their source. Contradictions are withheld — you see the evidence.'],
]

const PIPELINE_STEPS = [
  { key: 'parse', icon: 'file', label: 'Parse', detail: 'Docling reads pages, tables, charts, photos' },
  { key: 'chunk', icon: 'layers', label: 'Embed', detail: 'BGE embeddings create searchable vectors' },
  { key: 'index', icon: 'database', label: 'Store', detail: 'MongoDB Atlas vector + text search index' },
  { key: 'ask', icon: 'chat', label: 'Verify', detail: 'Retrieve, draft, verify, decide — all automatic' },
]

const FEATURES = [
  { icon: 'shield', title: 'NLI Verification', desc: 'Every claim is tested against source passages using a DeBERTa-based language inference model.' },
  { icon: 'eye', title: 'Evidence Trail', desc: 'See exactly which passage supports each claim, with highlighted quotes and page references.' },
  { icon: 'zap', title: 'Fast Processing', desc: 'Documents are parsed, chunked, and indexed in minutes. Ask questions as soon as processing completes.' },
  { icon: 'chart', title: 'Trust Scoring', desc: 'Calibrated trust scores tell you how confident the system is in each verified answer.' },
]

function PipelineDiagram() {
  return (
    <div className="flex items-center gap-0">
      {PIPELINE_STEPS.map((step, i) => (
        <div key={step.key} className="group flex items-center">
          <div className="relative flex flex-col items-center gap-2.5 px-4 text-center">
            <div className="grid h-14 w-14 place-items-center rounded-xl border border-line-strong bg-hover text-muted transition-colors group-hover:border-cotton group-hover:text-cotton sm:h-16 sm:w-16">
              <Icon name={step.icon} size={24} strokeWidth={1.5} />
            </div>
            <span className="text-sm font-medium text-soft">{step.label}</span>
            <span className="pointer-events-none absolute top-[72px] hidden w-[180px] rounded-md bg-noir/95 px-3 py-2 text-[12px] text-muted shadow-lg group-hover:block">
              {step.detail}
            </span>
          </div>
          {i < PIPELINE_STEPS.length - 1 && (
            <div className="flex h-px w-6 items-center sm:w-10">
              <span className="h-px w-full bg-line-strong" />
              <span className="h-0 w-0 border-y-[3px] border-l-[5px] border-y-transparent border-l-line-strong" />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function DemoCard() {
  return (
    <div className="relative flex flex-col gap-5 rounded-[20px] bg-cotton p-8 text-left text-noir shadow-[0_30px_60px_-20px_rgba(0,0,0,.65),0_0_0_1px_#2e2c2a]">
      <span className="absolute -top-3 -right-3 grid h-10 w-10 place-items-center rounded-xl bg-noir text-ok shadow-lg"><Icon name="check" size={20} strokeWidth={2.4} /></span>
      <span className="absolute -bottom-3 -left-3 grid h-10 w-10 place-items-center rounded-xl bg-noir text-cherry shadow-lg"><Icon name="shield" size={20} strokeWidth={1.8} /></span>

      <div className="flex items-center gap-3 rounded-[12px] border border-rule bg-paper px-5 py-3.5">
        <Icon name="search" size={20} className="flex-none text-graphite" />
        <span className="font-display text-lg font-semibold leading-tight sm:text-xl">What was the market growth in 2023?</span>
      </div>

      <div className="flex items-center gap-2 text-xs text-graphite">
        {['Searched 5 docs', '8 passages', '3 claims checked'].map((s) => (
          <span key={s} className="flex items-center gap-1.5 rounded-full border border-rule bg-paper px-3 py-1">
            <Icon name="check" size={11} strokeWidth={2.4} className="text-ok-line" />{s}
          </span>
        ))}
      </div>

      <div className="text-[15px] leading-relaxed">
        <p className="m-0">The market grew by <strong>114.3%</strong> over the previous year. <span className="rounded-[3px] bg-ok-bg px-1 text-ok-ink text-[13px]">C1 p.3</span> The increase amounted to <strong>418 billion yen</strong>. <span className="rounded-[3px] bg-ok-bg px-1 text-ok-ink text-[13px]">C2 p.3</span></p>
      </div>

      <div className="flex flex-wrap items-center gap-4 border-t border-rule pt-4 text-sm">
        <span className="inline-flex items-center gap-1.5 rounded-full bg-[#2a3e28] px-3 py-1 text-xs font-medium text-[#8DB87A]">
          <Icon name="check" size={12} strokeWidth={2.4} />Verified
        </span>
        <span className="text-graphite">Trust <strong className="font-semibold text-noir tabular">92</strong></span>
        <span className="text-graphite">2 of 2 supported</span>
      </div>
    </div>
  )
}

export default function Landing() {
  return (
    <main>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <GridBackdrop />
        <HeroArt />
        <div className="relative mx-auto flex max-w-[1440px] flex-col gap-10 px-6 pt-20 pb-20 sm:px-8 lg:flex-row lg:items-center lg:gap-14 lg:px-12 lg:pt-28 lg:pb-24">
          <div className="flex flex-col gap-6 lg:flex-[0_0_460px] xl:flex-[0_0_520px]">
            <p className="m-0 inline-flex w-fit items-center gap-2 rounded-full border border-line-strong bg-noir px-3 py-1.5 text-sm text-muted">
              <Icon name="shield" size={14} className="text-cherry" />NLI Verification Engine
            </p>
            <h1 className="m-0 font-display text-[clamp(40px,5.5vw,72px)] leading-[1.05] font-semibold tracking-[-0.01em]">
              Answers checked against the page.
            </h1>
            <p className="m-0 max-w-[42ch] text-lg leading-relaxed text-soft">
              Upload documents, ask questions. Every claim is verified by a language-inference model — supported answers show their source, contradictions are withheld.
            </p>
            <div className="flex flex-wrap gap-3">
              <Button size="lg" onClick={() => navigate('/upload')}><Icon name="upload" />Upload documents</Button>
            </div>
            <PipelineDiagram />
          </div>
          <div className="min-w-0 flex-1">
            <DemoCard />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="mx-auto max-w-[1440px] px-6 pt-24 pb-8 sm:px-8 lg:px-12">
        <div className="mb-3 flex items-center gap-3">
          <Display className="text-[44px] sm:text-[52px]">How verification works</Display>
          <HelpButton topic="Each question goes through 4 steps: retrieve relevant passages, draft an answer with citations, check every claim via NLI, then decide whether to show or withhold the answer." />
        </div>
        <p className="m-0 mb-12 max-w-[55ch] text-base leading-relaxed text-muted">Four steps run for every question. The answer only appears after the last one passes.</p>
        <ol className="m-0 grid list-none grid-cols-1 gap-5 p-0 sm:grid-cols-2 xl:grid-cols-4">
          {STEPS.map(([key, title, body], i) => (
            <li key={key} className="flex flex-col gap-4 rounded-[14px] border border-border bg-card px-7 py-8 transition-all hover:border-line-bright hover:-translate-y-1">
              {STEP_ART[key]}
              <span className="font-display text-[32px] leading-none font-semibold text-cherry">{i + 1}</span>
              <h3 className="m-0 text-xl font-semibold">{title}</h3>
              <p className="m-0 text-sm leading-relaxed text-soft">{body}</p>
            </li>
          ))}
        </ol>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-[1440px] px-6 pt-24 pb-8 sm:px-8 lg:px-12">
        <Display className="mb-10 text-[44px] sm:text-[52px]">What Argus does</Display>
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="flex flex-col gap-4 rounded-[14px] border border-border bg-card p-7 transition-all hover:border-line-bright hover:-translate-y-1">
              <div className="grid h-12 w-12 place-items-center rounded-xl border border-line-strong bg-hover text-muted">
                <Icon name={f.icon} size={22} strokeWidth={1.5} />
              </div>
              <h3 className="m-0 text-lg font-semibold">{f.title}</h3>
              <p className="m-0 text-sm leading-relaxed text-soft">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="mx-auto max-w-[1440px] px-6 pt-24 pb-28 sm:px-8 lg:px-12">
        <div className="flex flex-col items-center gap-6 rounded-[var(--radius-xl)] border border-border bg-card px-8 py-16 text-center">
          {STEP_ART.upload}
          <Display className="text-4xl sm:text-5xl">Ready to verify your documents?</Display>
          <p className="m-0 max-w-[50ch] text-base text-muted">Upload 4–5 PDF or Word files. Argus will process, embed, and index them so you can ask verified questions.</p>
          <Button size="lg" onClick={() => navigate('/upload')}><Icon name="upload" />Get started</Button>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border">
        <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4 px-8 py-5 lg:px-12">
          <div className="flex items-center gap-3">
            <Icon name="shield" size={20} strokeWidth={1.8} className="text-cherry" />
            <span className="font-display text-xl font-semibold text-cotton">Argus</span>
          </div>
          <span className="text-xs text-faint">Docling · MongoDB Atlas · DeBERTa · Groq</span>
        </div>
      </footer>
    </main>
  )
}
