# Argus — Rebuild Prompt (core-only, hostable)

## Role
You are a senior ML / AI engineer (RAG, embeddings, NLI, MongoDB Atlas, LLM APIs). You are working in the existing repo `argus-rag-nli-verification`. Your job: reduce Argus to its core, fix what is broken, replace the hand-tuned trust score with a learned one, add a separate evaluation, and make it deployable as a web app.

## Product (the only scope)
Argus is a RAG system that checks its own answers.
1. **Ingest:** the user uploads PDFs → Docling parse → chunks → BGE embeddings → MongoDB Atlas (original PDF in GridFS).
2. **Ask:** question → vector + keyword search → RRF → cross-encoder rerank → LLM answers as **claims, each citing a passage and quoting it**.
3. **Verify:** NLI (premise = cited passage, hypothesis = claim) + number check + quote check → a label per claim.
4. **Score:** trust score 0–100 per answer + decision: **Verified / Flagged / Withheld / Not in documents**.
5. **Show:** answer with coloured claims, evidence cards, page preview with a highlight box, and a chart drawn from table cells when the evidence is a numeric table.
6. **Prove:** a separate `eval/` runner shows the system works.

Anything not needed for 1–6 is out.

## Principles
- **KISS / YAGNI:** the smallest change that works. No new abstractions without a second user.
- **SOLID where it's cheap:** one job per module, and each shared job has one home (`config.py`, `db/client.py`, `models.py`, `generation/llm.py`, `pipeline.py`).
- **Don't hand-roll:** use library code (scikit-learn, scipy, rapidfuzz, Docling `HybridChunker`, pymongo, sse-starlette, an existing word-to-number library). Write logic yourself only when no library fits.
- **Reuse before rewrite:** modules that already work stay. Change them only where this prompt says so.
- **Every tunable number lives in `config.py`.** Learned values live in one JSON file.
- No bare `except`; use `logging`, not `print`; type hints on public functions; `ruff` clean; unit tests make no network calls.

## Hard rules (do not break)
- **No `git commit`, `git push`, branch creation or any other git write.** Read-only git (`status`, `diff`, `log`) is fine. The user commits.
- **Never edit or print `.env`** or any secret. Read keys through `config.py` only.
- **Don't delete code.** Move removed files to `_archive/<original path>` and add `_archive/` to `.gitignore`.
- Don't delete or modify `data/samples/`, `data/fever/` or `data/cache/`.
- No LangChain, no FAISS, no vision model, no image generation, no new database collections beyond the list below, no new frontend libraries except one chart library if needed (prefer `recharts`).
- Don't deploy anywhere. Build the Docker image locally only.
- **Time-box:** if a step takes more than about 45 min of work or 3 failed attempts, stop and report rather than pushing on.

## Phase 0 — Backup and baseline (stop and report at the end)
1. `tar czf _xfer/backup_before_core_<date>.tgz backend frontend/src scripts tests eval docs pyproject.toml`
2. Run `python -m pytest`, `ruff check .` and `cd frontend && npm run build`. Record the results as the baseline.

## Phase 1 — Verify the infrastructure (stop if anything fails)
Extend `scripts/check_setup.py` so that a single run checks and prints PASS/FAIL for:
- `.env` has `MONGO_URI` and `GROQ_API_KEY` (names only, never values).
- **MongoDB:** `ping`; database `DB_NAME` reachable; GridFS put/get/delete of a 1 KB test file; `chunks_vec` and `chunks_text` exist and are `queryable`.
- **Groq:** every model in `GROQ_MODELS` is in `models.list()`; one JSON-mode call returns valid JSON; report latency.
- **Models:** BGE embedder, reranker and NLI load; one embedding has dim 768; one NLI pair returns three probabilities that sum to 1.
- **Smoke test (`--smoke`):**
  - Create a temporary dataset and ingest `data/samples/nasa/astronaut_selection_and_training.pdf`.
  - Wait until it's searchable, ask 3 fixed questions and assert that each result has a decision, a trust score in 0–100, claims and evidence.
  - Delete the temporary dataset and confirm no chunks, documents or GridFS files are left behind.

Exit code 0 only if everything passes.

## Phase 2 — Remove what isn't core (move to `_archive/`)
- **Calibration:** `backend/calibration/` (synthetic, registry, feedback, per-dataset thresholds), the calibration routes, `worker.calibration_job`, `scripts/cal_progress.py`, and the `calibration_examples`, `calibration_registry` and `fever_validations` collections.
- **Vision:** `ingestion/assets.py` vision calls, `generation/llm.call_vision`, figure crops in GridFS `images`, the `derived` field and derived-only logic.
- **Repair:** the repair loop (`repair_answer`, the second attempt in `gate.py`, `REPAIR_*` prompts).
- **Follow-ups:** the follow-up rewrite and `recent_turns` (keep simple sessions: a chat groups queries; each question is answered on its own).
- **Misc:** `parse_plain.py`, the `/activity` route and frontend dock, the read-only demo flag, the `/assets/{id}/image.png` route.
- **Frontend:** remove the parts that call removed routes. Keep the datasets, upload, chat, evidence, page preview and a simple Analytics page (decision mix, trust histogram, latency, query log).

**Final MongoDB layout:**
- `datasets`, `documents`, `chunks`, `queries` and `sessions` (sessions only if kept minimal; otherwise put `session_id` on `queries`).
- GridFS `files` for original PDFs only. GridFS stays because page previews render from the original PDF, documents over 16 MB can't go in a normal record, and the host disk isn't persistent.
- Update `db/indexes.py` to match.

## Phase 3 — Fix the core checks
1. **Numbers:**
   - Parse number words and scale words with a library ("seven" = 7, "1.5 million" = 1,500,000), on both the claim and the evidence side. Keep the sign on negative numbers.
   - Tests: "seven years" vs "7 years" passes; "nine years" vs "7 years" fails; "$1.5 million" vs "$1,500,000" passes.
2. **Quote:** a quote must be at least `QUOTE_MIN_CHARS` (config, default 15) and match with `partial_ratio ≥ 90`. Test: a quote of just "7" is not found.
3. **Contradiction** comes only from the chunk(s) the claim cites (fall back to the best-entailing chunk if it cites nothing). Unrelated passages must not block an answer.
4. **Chunks fit the verifier:** use Docling `HybridChunker` with the NLI tokenizer budget, so no chunk is truncated before NLI. Log a warning if a premise is ever cut.
5. **Ingestion robustness:**
   - If the index wait times out, leave the document `indexing` and retry on the next status poll; never delete finished chunks.
   - On a failed ingest, delete its GridFS file.
   - Ingestion runs in one background worker thread.
6. **Frontend `ask()`:** if the stream ends without a `result` or `error` event, call `onError("connection closed")`.

## Phase 4 — Learned trust score (replace all hand-set values)
One global calibration, fitted offline, stored in `backend/calibration/trust.json` (version, data sources, fit date, metrics). Small `scripts/fit_trust.py`; the app only reads the JSON.

1. **Claim probability:** temperature-scale the NLI logits (`scipy.optimize.minimize_scalar` on NLL) using the existing FEVER-NLI 600-pair sample (`eval/fever_data.load_sample_pairs`).
2. **Answer trust:**
   - Data: RAGTruth (public, human-labelled RAG answers). Download a fixed subset of about 1,500 answers with a script and cache it under `data/ragtruth/` (git-ignored).
   - Label: answer is faithful = no hallucination span.
   - Run each answer through the **same** `verify_claims` code, with the source context as evidence and answer sentences as claims (pySBD).
   - Features: min, mean and max-contradiction support, share supported, number mismatches, quote match rate, n_claims.
   - Model: `sklearn` `LogisticRegression`, without class weights.
   - Split: fit 60% / cal 20% / test 20%, fixed seed, split by source document.
   - Trust = `round(100 × P(faithful))`.
3. **Cut-offs (on the cal split only):**
   - **Verified:** the lowest trust threshold whose 95% Clopper–Pearson upper bound on error is ≤ `RISK_VERIFIED` (config, 0.05). Search thresholds that each have at least 100 accepted examples (the chosen set depends only on scores, not labels), in fixed order, and stop at the first failure.
   - **Withheld:** any claim with calibrated contradiction ≥ the threshold whose false-withhold rate upper bound is ≤ `RISK_WITHHOLD` (0.02).
   - Everything else is Flagged.
   - If a target can't be met, fail loudly in the script. Never fall back silently.
4. **Report on the test split:** Brier score, ECE, AUROC, and the observed error of Verified answers against the target. Write these into `trust.json` and show them on the Analytics page.
5. **Only human-set numbers:** `RISK_VERIFIED` and `RISK_WITHHOLD`, documented as policy.

## Phase 5 — Charts from evidence (no images)
- When a cited chunk is a table, return `chart: {type, labels, series}` built **only from the table cells**: pie for one numeric column whose values are shares of a whole, bar for categories, line when the first column is years or dates. Otherwise return `null`.
- Use pandas for parsing. Render with one chart library in the evidence card, labelled "From table, p.N".

## Phase 6 — Evaluation (`eval/`, separate from the app)
`python -m eval.run --all` writes `results/<name>_<date>.json` and a short `results/REPORT.md`:
1. **Hallucination detection (RAGTruth test split):** precision, recall, F1, AUROC; confusion matrix.
2. **Calibration:** ECE, Brier score, reliability-diagram PNG (matplotlib).
3. **Injected errors (NASA chunks):** take 100 chunk-grounded correct claims and create number swap, entity swap and negation versions in code (use the LLM only for negation). Report the catch rate per type and the false-alarm rate on the correct claims.
4. **Retrieval:** for 100 LLM-written questions with a known gold chunk, report recall@5 and MRR for vector, keyword and hybrid + rerank.
5. **End-to-end headline:** share of hallucinated answers shown with the gate vs without it, and coverage, each with bootstrap 95% CIs (`scipy.stats.bootstrap`).

No hand-labelled golden set in this pass; leave a `data/golden/README.md` template for later.

## Phase 7 — Hosting
- Multi-stage `Dockerfile`: build the frontend; Python 3.11 slim with CPU torch; download models at build time; `uvicorn backend.main:app` on port 7860; FastAPI serves `frontend/dist`.
- Default NLI model: `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` (CPU-friendly). The large model is a config switch.
- Rate-limit `/api/ask` (simple per-IP limit), cap the upload size and the number of documents per dataset.
- Make CORS configurable; secrets come from environment variables only.
- `docker build` and run locally, then `scripts/check_setup.py --smoke` against the container. **Don't deploy.**
- Update `README.md`: what it is, architecture, setup, run, evaluate, deploy.

## Final check (do all, then report)
- `pytest`, `ruff check .` and `npm run build` pass.
- `scripts/check_setup.py --smoke` passes against the real MongoDB Atlas and Groq.
- The Docker container answers a question end to end.
- `git status` shows changes only, with **no commits made**.

## Report back (keep it short)
1. What was removed (paths in `_archive/`) and what was changed, one line each.
2. Phase 1 and final check results (PASS/FAIL per item).
3. Trust-score metrics and evaluation headline numbers.
4. Anything stopped by the time-box, with the reason.
5. Suggested commit message(s), for the user to run.
