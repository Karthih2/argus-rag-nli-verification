# Argus

**Claim-level hallucination gating for RAG over mixed-content PDFs, with self-calibrating trust.**

Argus answers questions over your own PDFs and checks every claim in the answer against the source
before showing it. Supported claims are shown, weak ones are flagged, and a contradicted answer is
withheld and replaced by the evidence. Thresholds and the trust score are learned per dataset, first
from synthetic examples generated from your documents, then from your feedback.

The full design is in [`docs/Argus Spec.md`](docs/Argus%20Spec.md); progress is in
[`docs/argus_status.md`](docs/argus_status.md).

## How a question flows

```text
Question ─► rewrite follow-up (last 3 turns) ─► $vectorSearch ‖ $search ─► RRF ─► rerank ─► context
         ─► LLM: claims + citations + exact quotes ─► NLI + quote + number checks per claim
         ─► ACCEPT / ACCEPT_LOW_CONFIDENCE / WARN / BLOCK / NO_SUPPORT (one repair on WARN/BLOCK)
         ─► answer + score card + highlighted evidence
```

## Project structure

```text
backend/
├── main.py              FastAPI app: /api routes + built frontend at /
├── config.py            every setting and fallback value (reads .env)
├── models.py            BGE embedder, reranker, DeBERTa NLI (loaded once)
├── pipeline.py          run_question(): one question end to end (API, CLI, eval)
├── sessions.py          conversations, follow-up rewrite, running totals
├── library.py           create datasets; delete documents/datasets with everything derived
├── worker.py            background jobs (ingest → calibrate), one at a time
├── common/              ids, text helpers, number parsing
├── db/                  MongoDB client + index definitions
├── ingestion/           intake → Docling parse → assets → chunks → embed → report
├── retrieval/           Atlas vector/text search, RRF fusion, reranker, context builder
├── generation/          Groq client (cache + fallback), prompts, answer drafting
├── verification/        NLI, checks, claim labels, gate + repair, trust features
├── calibration/         synthetic examples, temperature, trust model, thresholds, registry, feedback
└── api/routes/          one file per resource
frontend/src/            React + Tailwind, no extra packages: pages/, features/ (answer, evidence, art),
                         components/ (dock, upload, charts, shadcn-style ui/), lib/, api/client.js
scripts/                 check_setup, seed_demo, chat (CLI), download_fever, run_fever_validation
eval/                    FEVER data loader (experiments E0–E6 go here)
tests/                   unit tests: no network, fake NLI/LLM
data/samples/nasa/       demo + test PDFs (committed)
data/fever/sample_ids.json   fixed 600-pair FEVER sample (committed)
data/golden/             hand-written golden set (to be written)
docs/                    spec, status
```

Each shared job has exactly one home (settings → `config.py`, Mongo → `db/client.py`, models →
`models.py`, every Groq call → `generation/llm.py`, every prompt → `generation/prompts.py`,
numbers → `common/numbers.py`, one question → `pipeline.py`).

## Setup (Windows, from the repo root)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r backend\requirements.txt
copy .env.example .env        # then fill in MONGO_URI and GROQ_API_KEY
python -m scripts.check_setup # MongoDB, Atlas indexes, Groq models, one real Groq call
python -m scripts.download_fever
```

`.env` keys are listed in `.env.example`. In Atlas, allow your IP under Network Access.

## Run

```powershell
python -m scripts.seed_demo          # NASA dataset: ingest 5 PDFs + calibrate (add --fresh to redo)
python -m scripts.chat               # CLI chat with per-claim verdicts
uvicorn backend.main:app --reload    # API on http://localhost:8000
cd frontend; npm run dev             # UI on http://localhost:5173 (proxies /api to :8000)
cd frontend; npm run build           # then the API serves the app at http://localhost:8000
python -m pytest                     # unit tests
ruff check . ; ruff format .         # lint / format
python -m scripts.run_fever_validation  # NLI health check (stores result for Analytics)
```

## What stays local (see `.gitignore`)

`.env`, `venv/`, `models/` (Hugging Face downloads), `frontend/node_modules` and `dist`,
`data/cache/` (LLM cache), `data/fever/*.parquet`, `data/samples/anime/`, `data/uploads/`,
`docs/reports/*.pdf`, `logs/`, `.claude/`.
