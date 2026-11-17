# Argus — Status and Demo Readiness

Reviewed: 30 Oct 2026. Benchmark: `docs/Argus Spec.md`.

---

## 1. Done

**Repo**
- New layout in place: `backend/`, `frontend/`, `scripts/`, `eval/`, `data/samples/`, `docs/`.
- New `.gitignore`, `.env.example`, `backend/requirements.txt`.
- FEVER-NLI dev split downloaded; fixed 600-pair sample in `data/fever/sample_ids.json`.

**Backend**
- Config via pydantic-settings; MongoDB client + all 9 collection accessors + GridFS (`files`, `images`).
- Regular indexes and Atlas `chunks_vec` / `chunks_text` index creation (`db/indexes.py`).
- Ingestion: SHA-256 dedupe, GridFS storage, Docling parse (tables, figures, picture classification, OCR), plain pdfplumber parser (E0 baseline), table row-group + whole-table chunks, number/quote enrichment, BGE embeddings as BinData float32, extraction report.
- Retrieval: `$vectorSearch` + `$search` with dataset/document filters, RRF fusion, BGE reranker, context builder with neighbours and token cap.
- Generation: Groq JSON mode, model fallback chain, prompt-hash cache, vision call, Pydantic validation with retry and pySBD fallback.
- Verification: DeBERTa NLI with temperature scaling, quote / quotation / number / derived-only checks, claim labels, answer decisions, one repair pass, blocked reason, trust features.
- Calibration: synthetic QA + mutations (number, negation, addition, wrong-chunk), fit/cal/test splits, temperature fit, logistic trust model with Brier promotion, Clopper-Pearson fixed-sequence thresholds, versioned registry.
- Sessions with follow-up rewrite and `$slice: -3` recent turns.
- `run_question()` end-to-end pipeline storing full query traces.
- FastAPI routes: datasets, documents, sessions, ask (SSE), queries, feedback, calibration, analytics, FEVER, health, page preview PNG.

**Scripts**
- `check_setup`, `download_fever`, `ingest_nasa`, `calibrate_nasa`, `chat` (CLI), `run_fever_validation`.

**Frontend**
- Vite + React + Tailwind with spec colour tokens.
- Dataset list, create, single-PDF upload, chat view with SSE, decision banner, score card, claims, evidence panel, feedback buttons, details panel.
- `AnalyticsPage.jsx` exists.

---

## 2. Critical bugs (demo breaks)

| # | Where | Problem | Fix |
|---|---|---|---|
| 1 | `api/routes/documents.py` → `ingestion/intake.py` | Upload passes `str` path; `ingest_pdf` calls `.read_bytes()` → every UI upload fails. Original filename is replaced by a UUID. Temp file never deleted. | Pass `Path`, pass original filename through, delete temp file in `finally`. |
| 2 | `ingestion/parse_docling.py` `_bbox_from_cluster` | `prov.page` does not exist → bbox never normalised (raw PDF points). Docling bbox origin is bottom-left → y is flipped. Highlights land in the wrong place. | Use `doc.pages[prov.page_no].size`, convert with `bbox.to_top_left_origin(page_h)`, then normalise. |
| 3 | `generation/llm.py` `call_vision` | Cache key ignores the image → every chart/photo after the first gets the same cached description. | Include image hash in the cache key. |
| 4 | `ingestion/pipeline.py` | Derived (vision) text is matched against the hashed `chunk _id` → never attached. `asset_id` never set on figure chunks. | Map `element_path → derived / asset_id` before chunking and set on the chunk directly. |
| 5 | `api/routes/pages.py`, `documents.py` delete | GridFS id stored as `str`, used without `ObjectId(...)` → page preview 404/500, PDF delete silently fails. | Wrap with `ObjectId` (or store the ObjectId). |
| 6 | `pipeline.py` + `verification/gate.py` | After a successful repair, the **original failed answer text** is returned with the repaired claims. | Return the repaired `answer` from `attempt_repair` and use it. |
| 7 | Frontend ↔ API field names | `ClaimList`/`DetailsPanel` read `verdict`, `nli_label`, `numbers_ok`, `quote_ok`, `evidence_ref`; API sends `label`, `checks.numbers_ok`, `checks.quote_match`, `highlight.ref`. `EvidenceList` reads `file`, `element_type`, `rerank_score`; API sends `file_name`, `type`, `rerank`. Latency keys differ (`retrieval/generation/verification` vs `retrieve/llm/verify`). Analytics reads `cal.status`, `cal.live`, `fever.total_pairs`, `avg_latency_ms`; API sends `calibrated`, `live_versions`, `n_pairs`, `latency_ms_per_pair`. | Align frontend to the API response (spec 12.1). |
| 8 | `api/routes/ask.py` | Sync `run_question()` runs inside an async generator → blocks the whole server for every question. | `await run_in_threadpool(...)` or a queue; emit real stage events. |
| 9 | Git | All new work (`backend/`, `frontend/`, `eval/`, `docs/`, new scripts) is **untracked**; deletions uncommitted. | Commit and push. |

---

## 3. Correctness fixes (results are wrong without these)

**Calibration (the "≤5% risk" claim is not valid yet)**
- Label leakage: `quote_match_rate` and `number_mismatches` are set from the mutation type → trust model learns the label directly. Compute features by running examples through `run_question()` / the gate (spec 10.1 step 4).
- `top1_rerank` reads `_rerank_score` from stored chunks (never present) → constant 0.5.
- Thresholds are fitted on **trust score** but the gate compares them to **NLI support**. Fit `τ_accept`/`τ_low` on claim support, or gate on trust — pick one and make both match.
- `τ_rel` uses answer-correctness labels instead of gold-chunk labels.
- `assign_splits` reshuffles all examples on every run → test/cal leak across versions. Assign split once at creation.
- Calibration never runs automatically after ingestion; feedback never becomes `calibration_examples`; no refit every 10 feedback labels.
- Entity-swap mutation missing.

**Ingestion**
- Paragraph merging to 320 tokens (HybridChunker) not used → one chunk per Docling text item (very short chunks).
- No KPI, list, footnote, quote-boundary, header/footer, cover-page or TOC-exclusion handling (only heading-text TOC check).
- Table captions always empty (`TableItem.caption` is not a field; use `caption_text(doc)`).
- `MAX_PAGES` not enforced; `pages_done` not updated per page; `ocr_pages` hard-coded 0.
- Document marked `ready` before Atlas indexes return it (spec 5.8 ready check missing).
- Metadata (doc number, effective date) not extracted.

**Retrieval / verification**
- Context dedupe by `seq // 3` drops distinct adjacent chunks (e.g. table row groups). Dedupe by text overlap instead.
- Neighbour chunks get citable refs (`C#`); only the prompt says "do not cite". Exclude them from `ref_to_chunk`.
- Number and quote checks run only against the best-NLI chunk, not the cited chunk(s).
- `attempts` stores one attempt with `model: "groq"`; store both attempts and the real model name.
- Result missing `session_summary`, `score_card.calibration`, `highlight.span` (spec 12.1).

**Data cleanup**
- `delete_dataset` leaves assets, GridFS files/images, sessions, queries.
- `delete_document` leaves GridFS images; no refit after delete.

**Setup script**
- `check_setup.py` reads `MONGO_DB`; config uses `DB_NAME`.

---

## 4. Frontend gaps

- Analytics page not routed from `App.jsx`.
- No document picker per chat (always all docs → no cross-document mode toggle).
- No session list / reopen; no chat header totals.
- Upload: one file at a time, no status polling, no extraction report view, no delete.
- No citation chips inside the answer, no claim-coloured sentences.
- No page preview with highlight (endpoint exists, not used).
- No table rendering, figure crops, or "derived" marking on evidence cards.
- No example question chips (from synthetic questions).
- No calibration badge detail ("Calibrated vN · 5% risk"), no reliability diagram, no trust/latency charts, no query log.
- Mobile layout: evidence panel hidden below `lg`, no drawer.
- Leftovers: `index.html` title "frontend", template `App.css`, `hero.png`, `react.svg`, `vite.svg`, template `README.md`.

---

## 5. Hosting (nothing exists yet)

- `Dockerfile`: multi-stage — build frontend, then Python 3.11 + CPU torch; pre-download BGE, reranker, DeBERTa and Docling models at build time; serve on port 7860.
- Resolve `frontend/dist` path from file location, not CWD.
- FastAPI lifespan: preload all models, run `ensure_all_indexes()`.
- `/api/health`: add model-loaded and search-index-ready checks.
- Pin versions in `requirements.txt`.
- Background ingestion: replace `BackgroundTasks` with a worker loop on `processing.status = queued` (spec `worker.py`), one job at a time.
- `scripts/seed_demo.py`: create NASA dataset, ingest, calibrate (merge `ingest_nasa` + `calibrate_nasa`).
- Public-demo protection: rate-limit `/api/ask`, cap uploads per dataset, disable dataset/document delete on the NASA demo dataset (or a read-only demo flag). Groq key and Atlas are otherwise open to abuse.
- CORS: drop localhost-only list (same-origin when served by FastAPI) or make it configurable.
- HF Space secrets: `MONGO_URI`, `GROQ_API_KEY`. Atlas network access must allow the Space.
- Measure p50 latency on 2 vCPU; if > 8 s: ONNX int8 for NLI/reranker, rerank 20, or base NLI model.

---

## 6. Evaluation (not started)

- Golden set: `data/golden/` has only a README (and it says `.json`; spec says `.jsonl`). Write 150 claims + 60 questions, annotation guide, Cohen's kappa.
- `eval/run_eval.py`, `eval/metrics.py`, `eval/experiments/e0…e6` missing.
- `results/` empty; no bootstrap CIs; no headline number.
- FEVER validation: script exists; run it and confirm the result is stored.
- Hand-check 50 synthetic examples.
- `tests/` empty — add unit tests for numbers, checks, aggregate, thresholds, fusion (no network).

---

## 7. Repo cleanup

- Delete legacy code not used by `backend/`: `src/`, `db/mongodb.py`, empty `eval_data/`.
- Rewrite `README.md` (currently describes the old Streamlit/FAISS app): what it is, architecture, setup, `.env`, seed, run, deploy, demo GIF, headline number.
- Add `Makefile` (`setup`, `seed`, `dev`, `eval`, `docker`).
- `backend/main.py` per spec (currently `backend/api/app.py`) — rename or update spec.

---

## 8. Order of work to a hostable demo

1. Commit current work.
2. Fix critical bugs 1–8.
3. Re-ingest NASA set; verify extraction report, bboxes, figure descriptions.
4. Fix calibration leakage and threshold/gate mismatch; recalibrate.
5. Align frontend to API; add page preview, document picker, analytics route, upload status.
6. Lifespan preload, worker, health checks, demo protection.
7. Dockerfile + seed script; deploy to HF Space + Atlas; measure latency.
8. README rewrite.
9. Golden set + eval harness + results (needed for report claims, not for the demo itself).
