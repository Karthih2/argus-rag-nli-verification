> **Note (18 Nov 2026):** this is the original full plan. The built system is the core version described in `README.md` and `docs/argus_rebuild_prompt.md` (no vision model, no repair loop, no follow-up rewrite, one global calibration in `backend/calibration/trust.json`).

# Argus Spec — Build Specification

**Argus: Claim-Level Hallucination Gating for RAG over Mixed-Content Documents, with Self-Calibrating Trust**

As of 21 Oct 2026 · This is the single source of truth for building Argus.

---

## 1. What Argus is

Argus answers questions over a user's own documents and checks every claim in the answer against the source before showing it:
- **Supported** claims are shown.
- **Weak** ones are flagged.
- **Contradicted** answers are withheld and replaced by the evidence.

The thresholds and trust score are learned per dataset, first from synthetic examples generated from the uploaded documents, then from user feedback.

- **Users:** create a dataset, upload PDFs, ask questions. NASA documents are the demo and test dataset; nothing in the code is NASA-specific.
- **In scope:** PDF files, English, single user, one or several documents per question, and **conversations**: a series of follow-up questions about text, tables, charts, KPIs or images, each answer verified and scored.
- **Out of scope:** login, other file types, fine-tuning.
- **Stack:** Python 3.11, FastAPI, React (Vite + Tailwind), MongoDB Atlas (Vector Search + Search + GridFS), Docling, Hugging Face Transformers, Groq, scikit-learn.

---

## 2. Problem

RAG retrieves the right passages but doesn't guarantee the answer reflects them. Models paraphrase, over-generalise and invent numbers while sounding confident. Tools such as RAGAS and TruLens measure this afterwards; they don't stop it reaching the user.

Real PDFs make it worse. Two-column text, tables with multi-line cells, charts whose numbers sit in a legend, KPI callouts, quotes and photos all get scrambled by plain text extraction. The retriever then can't find the evidence, and the verifier has nothing to check against.

Argus fixes both: structure-aware extraction so the evidence exists, then claim-level verification with thresholds learned from data rather than hand-set.

---

## 3. Features

1. **Structure-aware ingestion:** text, tables, charts, KPIs, quotes, lists and footnotes are each extracted in a suitable way, with page and position kept.
2. **Hybrid retrieval:** semantic search plus keyword search in MongoDB Atlas, fused and reranked, restricted to the selected documents.
3. **Quote-anchored answers:** each claim cites a passage and copies the exact supporting text.
4. **Claim-level verification gate:** NLI plus number and quote checks; answers are accepted, flagged, repaired once, or blocked.
5. **Hard block with evidence:** a contradicted answer is never shown; the user sees the source passage and why.
6. **Self-calibrating thresholds per dataset,** with a stated limit on the error rate of accepted answers.
7. **Transparency:** citation chips, per-claim scores, highlighted evidence on the page image, and an extraction report per document.
8. **Conversational Q&A:** users ask a series of questions in one chat, including follow-ups like "and what about table 3?". Each answer is verified on its own and gets its own score.
9. **Benchmark check:** an offline FEVER-NLI run for the verifier.

---

## 4. End-to-end flow

Argus is a normal RAG system with a verification layer added after generation (★ = what Argus adds).

**When the user uploads PDFs**
1. Extract content by type: text, tables, charts, KPIs, quotes, images (★ Docling, Section 5).
2. Chunk, embed and store the chunks in MongoDB Atlas (Sections 5–6).
3. ★ Calibrate: generate synthetic questions and wrong answers, then learn the thresholds and trust model (Section 10).

**When the user asks a series of questions in a chat**
1. ★ Rewrite a follow-up into a standalone question using the last 3 turns.
2. Embed the question; run vector search + keyword search; fuse and rerank (Section 7).
3. The LLM answers from the passages, ★ as claims with citations and exact quotes (Section 8).
4. ★ Verify each claim with NLI (passage = premise, claim = hypothesis) plus number and quote checks (Section 9).
5. ★ Decide: accept, partly verified, warn, repair once, or block and show the evidence.
6. Show the answer with its score card, citations and highlighted evidence (Section 11). The output format is in Section 12.1.

## 4.1 Architecture

```text
 Upload PDF ─► Intake (hash, dedupe, GridFS) ─► Parse (Docling) ─► Typed elements ─► Chunk ─► Enrich (numbers, quotes)
            ─► Embed (BGE) ─► chunks collection ─► Atlas Vector Search + Atlas Search indexes
            ─► Extraction report ─► Synthetic calibration examples

 Question ─► (rewrite follow-up using last 3 turns) ─► Embed ─► $vectorSearch ‖ $search ─► RRF fusion ─► Rerank ─► Context
          ─► Generate (claims + citations + quotes) ─► Verify each claim ─► Gate ─► (one repair) ─► Show
                                                          ▲
                                     calibration_registry (T, thresholds, trust model) per dataset
```

---

## 5. Ingestion and extraction

### 5.1 Intake

- PDF only; maximum 50 MB and 500 pages per file.
- Compute `sha256` of the file. If the same file is already in the dataset, skip it. (The repo currently has the ISS PDF twice.)
- Store the original in GridFS; it is needed for page previews.
- A background worker processes queued documents in batches of 10 pages, so the UI can show progress per page.

### 5.2 Parser: Docling

Docling (MIT licence, runs on CPU) handles what these PDFs need in one pipeline:
- layout detection
- reading order for two-column pages
- table structure
- figure detection and classification
- OCR only where a page has no text layer
- a bounding box for every element

Settings:

| Setting | Value | Why |
|---|---|---|
| Table structure | `accurate` | Policy tables have multi-line cells and bullets |
| OCR | Automatic (pages/regions without text only) | Scanned uploads still work; normal pages aren't slowed |
| Picture images | `generate_picture_images=True`, `images_scale=2` | Crops for image reading and the UI |
| Picture classification | `do_picture_classification=True` | Separates charts from photos and logos |

Keep the current pdfplumber pipeline as `parser="plain"`. It is the baseline for experiment E0.

### 5.3 Content types

| Content | Stored as | Text used as evidence | NASA example |
|---|---|---|---|
| **Body text** | `text` chunks | Paragraphs merged up to the token budget, never across a heading | Two-column ISS report and astronaut fact sheet |
| **Headings** | Heading path on each chunk | Added to the search text, not counted as evidence | "3. Policy Requirements › Retaining documentation" |
| **Lists** | Kept with their lead-in sentence | Lead-in + items | Policy "shall" lists |
| **Tables** | One `asset` (full cells) + `table` chunks | Row groups with the header repeated, written as "row, column = value", plus the caption. Tables of ≤ 15 rows also get one whole-table chunk. | Retention table (SI policy p.36), PII penalty table (IT rules p.11), ranking table (ISS p.2) |
| **Charts** | One `asset` (crop + transcription) + `figure` chunk | Caption + chart text from the PDF text layer (legend, labels) **+ separately** a vision-model transcription marked `derived` | ISS p.1: the totals "2534 / 576 / 175" are real text; the segment percentages are pixels only, so they are derived |
| **KPI callouts** | `kpi` chunk | The callout + its heading + the next sentence | "377 articles published in Top 100 journals" |
| **Quotes** | Offsets recorded on the chunk | Never split inside a quote | 17 long quotes in the SI policy |
| **Footnotes** | `footnote` chunks | As written | ISS citation notes |
| **Photos and diagrams** | `asset` (crop + description) + `figure` chunk | Caption (real text) **+ separately** a vision-model description marked `derived`, so image questions can be answered | ISS crew photos (p.5–6), astronaut fact-sheet photo |
| **Logos, decorative images** | `asset` only | Not searchable | Agency logos, word cloud (p.20), cover art |
| **Table of contents** | Document outline only | **Excluded from search** | SI policy p.1 |
| **Headers, footers, page numbers** | Dropped. Useful values ("Effective Date: May 28, 2024") go to `documents.metadata` | — | SI policy running header |
| **Blank or cover pages** | Page marked `cover` or `blank` | — | National Space Policy pp.1–2, 4 |

**Image reading (vision model).** Chart, photo and diagram crops go to the Groq vision model:
- **Charts:** copy the title, axes, legend and printed values exactly, infer nothing, return JSON.
- **Photos and diagrams:** describe what is visibly shown in 2–4 factual sentences (people, equipment, setting, any visible text), with no guessing of names or facts not visible.

Both results are stored as `derived`, so answers based on them are capped at "partly verified" and the UI shows the image. Image reading can be switched off per dataset, because it sends images to Groq.

### 5.4 The NASA test set

| File | Pages | Tables | Pages with images | What it tests |
|---|---|---|---|---|
| ISS Annual Highlights of Results | 72 | 15 | 26 | Two columns, charts, ranking table, photos, KPIs |
| NASA Scientific Integrity Policy | 43 | 10 | 5 | TOC, running header, policy tables, quotes |
| National Space Policy | 40 | 0 | 0 | Long prose, cover/blank pages |
| NASA Cybersecurity & IT Rules of Behavior | 13 | 3 | 0 | Multi-row penalty tables |
| Astronaut Selection and Training | 4 | 0 | 4 | Fact-sheet layout, photo captions |

That is 172 pages, about 700–900 chunks.

### 5.5 Chunking

- Docling `HybridChunker` with the BGE tokenizer: `max_tokens=320`, `merge_peers=True`, `repeat_table_header=True`. 320 tokens leaves room for the claim inside DeBERTa's 512-token limit.
- Chunks never cross a heading, a table boundary or a quote.
- Each chunk stores two texts:
  - `text`, the evidence (used for NLI and shown to the user).
  - `embed_text` = title + heading path + caption + `text` (used for embedding and keyword search).
- Vision-model text goes in a separate `derived` field.
- `chunk_id = sha1(file_sha256 + element_path + part)[:20]`, so re-ingesting overwrites instead of duplicating. `seq` gives the chunk's position in the document.

### 5.6 Enrichment (computed once at ingestion)

- `numbers[]`: each number with its normalised value, unit and position. This covers "3,285", "22 percent" = 22%, dates and durations ("7 years").
- `quotes[]`: positions of quoted spans.

### 5.7 Embedding

- `BAAI/bge-base-en-v1.5`, 768 dimensions. Passages have no prefix; queries use the BGE query instruction. L2-normalised.
- Stored as a BSON BinData `float32` vector (`pymongo` 4.10+, `Binary.from_vector`), about 3 KB per chunk.

### 5.8 Extraction report and ready check

Each document stores a report:
- pages by kind (text, table, chart, photo, cover, OCR)
- numbers of tables, charts and KPIs
- pages that produced no chunks

The UI shows it, so bad extraction is caught before it causes bad answers.

Atlas search indexes update a few seconds after a write. A document becomes `ready` only once a `$vectorSearch` filtered to it returns results.

---

## 6. Database (MongoDB Atlas)

### 6.1 Design rule

Store together what the app reads together. Every frequent read is one document or one index lookup. No array inside a document grows with the input.

Three schema patterns are used:

| Pattern | Where | Why |
|---|---|---|
| **Extended Reference** | `chunks` carry `file_name`, `doc_title`, `heading_path`, `page`; `queries.evidence[]` keeps a copy of each evidence text | Search results show citations without extra lookups; old answers stay auditable after re-ingestion |
| **Computed** | `chunks.numbers`, `chunks.quotes`, `documents.stats` | The checks and the library don't recompute on every request |
| **Subset** | `documents.outline`, `documents.pages`, `sessions.recent_turns` | The document card, document view and follow-up context are each one read; full detail stays in `chunks`, `assets` and `queries` |

### 6.2 Why chunks are their own collection

1. **Access is per chunk.** Each query reads 20–30 chunks from different documents, never one document's full chunk list. One chunk document holds everything a search hit needs.
2. **Vector Search works on one vector per document.** Vectors nested inside an array of a parent document need extra configuration and return the whole parent for each hit.
3. **Size is unbounded.** At about 7 KB per chunk, the 16 MB document limit is reached at about 2,300 chunks, a ~600-page PDF. Any update would rewrite the whole large document.

### 6.3 Collections

Nine collections plus GridFS.

**`datasets`**: one per user dataset.
```json
{ "_id": "ds_nasa", "name": "NASA policies & reports", "description": "...",
  "settings": { "risk_alpha_accept": 0.05, "risk_alpha_low": 0.15, "risk_false_block": 0.02, "image_reading": true },
  "created_at": "..." }
```

**`documents`**: one per uploaded PDF.
```json
{ "_id": "doc_3f9c", "dataset_id": "ds_nasa",
  "file": { "name": "nasa_scientific_integrity_policy.pdf", "sha256": "...", "bytes": 1505210, "gridfs_id": "..." },
  "metadata": { "title": "NASA Guidelines for Promoting Scientific and Research Integrity",
                "doc_number": "NAII 1920.1", "effective_date": "2024-05-28", "page_count": 43 },
  "processing": { "status": "queued | parsing | embedding | indexing | calibrating | ready | failed",
                  "pages_done": 43, "pages_total": 43, "error": null },
  "stats": { "chunks": 188, "tables": 10, "charts": 0, "kpis": 3, "quotes": 17, "ocr_pages": 0 },
  "outline": [ { "level": 1, "title": "Policy Requirements", "page": 5 } ],
  "pages": [ { "n": 1, "kind": "toc", "chunks": 0 }, { "n": 36, "kind": "table", "chunks": 6 } ],
  "created_at": "...", "ready_at": "..." }
```
`pages` is bounded by the 500-page upload limit.

**`chunks`**: the search unit.
```json
{ "_id": "c_8b1e0f", "dataset_id": "ds_nasa", "document_id": "doc_3f9c", "seq": 141,
  "element_type": "text | table | table_full | figure | kpi | list | footnote",
  "text": "Records of complaints regarding research integrity ... Destroy 7 years after case is closed ...",
  "embed_text": "NASA Guidelines ... › Table 2: Retaining documentation from SI cases › ...",
  "derived": null,
  "embedding": "<BinData float32, 768>",
  "file_name": "nasa_scientific_integrity_policy.pdf", "doc_title": "NASA Guidelines ...",
  "heading_path": ["3. Policy Requirements", "Retaining documentation"],
  "page": 36, "bbox": [0.08, 0.31, 0.92, 0.47],
  "asset_id": "a_tbl_36_2",
  "numbers": [ { "raw": "7 years", "value": 7, "unit": "year", "span": [88, 95] } ],
  "quotes": [ [0, 212] ],
  "ocr": false }
```

**`assets`**: one per table or figure. Only the field matching `kind` is filled.
```json
{ "_id": "a_tbl_36_2", "document_id": "doc_3f9c", "kind": "table | chart | photo | diagram | logo",
  "page": 36, "bbox": [0.08, 0.20, 0.92, 0.70], "caption": "Table 2. Retaining documentation from SI cases",
  "table": { "header": ["Type", "Description", "Retention Schedule"], "rows": [["..."]] },
  "chart": { "text_layer": "Peer Reviewed Journals 2534 ...", "transcription": {}, "derived": true },
  "image": { "description": "A crew member works at an open equipment rack ...", "derived": true },
  "image_id": "<GridFS id>" }
```

**`sessions`**: one per conversation. Keeps only the last 3 turns, for rewriting follow-ups (Subset), plus running score totals for the chat header.
```json
{ "_id": "s_...", "dataset_id": "ds_nasa", "title": "Record retention", "document_ids": ["doc_3f9c"], "mode": "single",
  "recent_turns": [ { "q": "How long are case records kept?", "a": "...", "decision": "ACCEPT" } ],
  "turns": 6, "summary": { "ACCEPT": 4, "ACCEPT_LOW_CONFIDENCE": 1, "WARN": 0, "BLOCK": 1, "NO_SUPPORT": 0, "avg_trust": 84 },
  "updated_at": "..." }
```
`recent_turns` is kept to 3 with `$push` + `$slice: -3`. The full history is in `queries`.

**`queries`**: one per question; the full trace. Bounded at ≤ 8 evidence chunks, ≤ 10 claims and 2 attempts.
```json
{ "_id": "q_...", "dataset_id": "ds_nasa", "session_id": "s_...", "turn": 6, "ts": "...",
  "mode": "single | cross", "document_ids": ["doc_3f9c"],
  "question": "And for misconduct cases?", "standalone_question": "How long are research misconduct case records kept?",
  "evidence": [ { "ref": "C1", "chunk_id": "c_8b1e0f", "file_name": "...", "page": 36, "element_type": "table",
                  "text": "<copy>", "scores": { "dense": 0.71, "text": 12.3, "rerank": 0.84 }, "relevant": true } ],
  "attempts": [ { "n": 1, "model": "...", "not_found": false, "decision": "ACCEPT",
      "claims": [ { "text": "...", "cites": ["C1"], "quote": "Destroy 7 years after case is closed",
                    "quote_match": 1.0, "numbers_ok": true, "derived_only": false,
                    "nli": [ { "ref": "C1", "ent": 0.93, "neu": 0.05, "con": 0.02 } ],
                    "support": 0.93, "contra": 0.02, "label": "SUPPORTED" } ] } ],
  "decision": "ACCEPT", "trust": 91, "features": {},
  "calibration_versions": { "temperature": 3, "thresholds": 3, "trust_model": 3 },
  "latency_ms": { "retrieve": 420, "rerank": 610, "llm": 1900, "verify": 2300, "total": 5400 },
  "feedback": { "value": null, "reason": null } }
```

**`calibration_examples`**: synthetic and feedback examples.
```json
{ "_id": "...", "dataset_id": "ds_nasa", "document_id": "...", "source": "synthetic | feedback",
  "mutation": "none | number | negation | entity | addition | wrong_chunk",
  "label": 1, "nli_label": "entailment", "split": "fit | cal | test",
  "question": "...", "answer": "...", "gold_chunk_id": "...", "features": {}, "human_checked": false }
```

**`calibration_registry`**: every fitted version. The live version is the newest one with `status: "live"`.
```json
{ "_id": "...", "dataset_id": "ds_nasa", "param": "temperature | thresholds | trust_model", "version": 3,
  "status": "live | rejected", "value": {},
  "heldout": { "brier": 0.11, "ece": 0.04, "accepted_error_ucb": 0.049, "coverage": 0.71 }, "fitted_at": "..." }
```

**`fever_validations`**: one per offline benchmark run (Section 13).

**GridFS:** `files` (original PDFs) and `images` (figure crops).

### 6.4 Indexes

Atlas free clusters allow **3 search/vector indexes in total**. Argus uses 2, both on `chunks`.

Vector index `chunks_vec`:
```json
{ "fields": [
  { "type": "vector", "path": "embedding", "numDimensions": 768, "similarity": "cosine", "quantization": "scalar" },
  { "type": "filter", "path": "dataset_id" },
  { "type": "filter", "path": "document_id" } ] }
```

Search index `chunks_text`:
```json
{ "mappings": { "dynamic": false, "fields": {
  "embed_text":  { "type": "string", "analyzer": "lucene.english" },
  "dataset_id":  { "type": "token" },
  "document_id": { "type": "token" } } } }
```

Regular indexes:

| Collection | Index | Used for |
|---|---|---|
| `chunks` | `{document_id: 1, seq: 1}` unique | Neighbouring chunks, delete, re-ingest |
| `documents` | `{dataset_id: 1, "file.sha256": 1}` unique | Duplicate check |
| `documents` | `{"processing.status": 1}` | Worker queue |
| `queries` | `{dataset_id: 1, ts: -1}` | Query log, analytics |
| `queries` | `{session_id: 1, turn: 1}` | Showing a conversation |
| `sessions` | `{dataset_id: 1, updated_at: -1}` | Chat list |
| `calibration_examples` | `{dataset_id: 1, split: 1}` | Fitting |
| `calibration_registry` | `{dataset_id: 1, param: 1, version: -1}` | Live version, history |

**Storage:** the NASA set is about 25 MB including originals; each query is about 15 KB. The free tier's 512 MB is plenty for the demo.

---

## 7. Retrieval

0. **Follow-up rewrite.** From the second question in a chat onward, one short LLM call turns the question into a standalone question using `sessions.recent_turns` (e.g. "And for misconduct cases?" becomes "How long are research misconduct case records kept?"). Both versions are stored, and the UI shows the rewritten one under the question so the user can see how it was understood.
1. Embed the (standalone) question with the BGE query prefix.
2. Run two searches in parallel, both filtered to the dataset and the selected documents:
   - `$vectorSearch`: `limit=30`, `numCandidates=400`
   - `$search`: text on `embed_text`, limit 30
3. Fuse with Reciprocal Rank Fusion (k = 60) in Python. This works on any MongoDB version; the server-side `$rankFusion` stage needs a support case on 8.0.
4. Rerank the top 30 with `BAAI/bge-reranker-base` and keep the top 8.
5. Build the context:
   - Drop overlapping chunks.
   - Where a text chunk is the only hit from its section, add its neighbours (`seq ± 1`) as context only. Neighbours are visible to the model but can't be cited.
   - Cap at about 3,500 tokens.
6. Cross-document mode is the same pipeline with several document IDs. Nothing outside the selection is searched.

---

## 8. Generation

Groq, JSON mode, with a model fallback list. Required output:

```json
{ "answer": "One concise paragraph.",
  "claims": [ { "text": "Records of research integrity complaints are destroyed 7 years after the case is closed.",
                "cites": ["C1"], "quote": "Destroy 7 years after case is closed" } ],
  "not_found": false }
```

Rules in the prompt:
- Use only the numbered context.
- Make each claim one fact.
- Each claim cites a chunk and copies a verbatim `quote` from it.
- Copy numbers exactly as written.
- If the context doesn't answer the question, set `not_found: true`.

Validate the output with Pydantic and retry once on a parse failure. If `claims` is missing, split `answer` into sentences (pySBD) and use them as uncited claims. Cache responses by prompt hash so evaluation runs are repeatable.

---

## 9. Verification

### 9.1 NLI

- **Model:** `MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli`, loaded once at startup. The lighter `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` is the fallback if it's too slow.
- Label order is read from `config.id2label`. Probabilities are temperature-scaled: `softmax(logits / T)`.
- Each claim is checked against its cited chunks plus the top 3 relevant chunks, at most 4 per claim. All pairs run in one batch, with the premise truncated to fit 512 tokens.
- For the best-supporting chunk, the 1–3 sentence window with the highest entailment becomes the highlight in the UI.

### 9.2 Extra checks

| Check | Rule | Effect |
|---|---|---|
| **Quote** | The claim's `quote` must appear in the cited chunk (RapidFuzz `partial_ratio` ≥ 90). If the claim itself presents a quotation, that must match the source (≥ 95). | A missing evidence quote prevents SUPPORTED; a misquoted quotation makes the claim CONTRADICTED |
| **Numbers** | Every number or date in the claim must match a number in the supporting chunk after normalisation | Mismatch → at most UNVERIFIED; the UI says "Claim says 2,543; page 1 says 2,534" |
| **Derived only** | Only vision-model text supports the claim | At most WEAKLY_SUPPORTED; the UI shows "from AI reading of a chart/image — check the figure" |

### 9.3 Claim label

`support` = highest entailment over the checked chunks. `contra` = highest contradiction over relevant chunks only (reranker score ≥ `τ_rel`). Rules, checked in order:

| Condition | Label |
|---|---|
| Misquoted quotation, or `contra ≥ τ_block` | CONTRADICTED |
| Number mismatch | UNVERIFIED |
| `support ≥ τ_accept`, quote found, not derived-only | SUPPORTED |
| `support ≥ τ_low`, or derived-only with `support ≥ τ_accept` | WEAKLY_SUPPORTED |
| Otherwise | UNVERIFIED |

### 9.4 Answer decision and repair

| Condition (in order) | Decision |
|---|---|
| `not_found` | NO_SUPPORT: "Not in these documents" + closest passages |
| Any claim CONTRADICTED | BLOCK |
| All SUPPORTED | ACCEPT |
| All SUPPORTED or WEAKLY_SUPPORTED | ACCEPT_LOW_CONFIDENCE |
| Otherwise | WARN |

**Repair, at most once.** On BLOCK or WARN, send the model the failed claims with their reasons ("number not in source", "contradicted by C2") and ask it to correct or remove them. Verify the new draft from scratch. A blocked draft is never shown. If the repaired draft still fails, the user gets BLOCK (evidence only) or WARN (unverified sentences marked).

### 9.5 Trust score

`trust = round(100 × P(correct))`, from the dataset's trust model. Features:
- `min_support`, `mean_support`, `max_rel_contra`, `share_supported`, `n_claims`
- `quote_match_rate`, `number_mismatches`, `derived_only_share`
- `top1_rerank`, `rerank_gap`, `repaired`

The decision comes from the claim rules, so every block points at a specific claim and passage. The trust score is for ranking and analytics.

---

## 10. Adaptive calibration (per dataset)

Every number in the gate is fitted from data and versioned. `config.py` holds fallback values, used only until a dataset is calibrated; the UI labels them "fallback".

### 10.1 Synthetic examples (no human labels needed)

When a document is ready:

1. Sample `min(30, chunks/3)` chunks, spread across element types (text, tables, KPIs, charts, images).
2. The LLM writes a question each chunk answers and a cited correct answer → `label 1`, `nli_label: entailment`.
3. Each correct answer gets one or two mutations:

| Mutation | How | `label` | `nli_label` |
|---|---|---|---|
| Number / date swap | Code edits a number | 0 | contradiction |
| Negation | LLM rewrite | 0 | contradiction |
| Entity swap | Entity from the same dataset swapped in | 0 | contradiction |
| Unsupported addition | LLM adds a plausible detail not in the chunk | 0 | neutral |
| Wrong-chunk answer | Answer written for a different chunk | 0 | neutral |

4. Each example runs through the full pipeline and is stored with its features.
5. Split per dataset with a fixed seed: **fit 50% / cal 30% / test 20%**.
6. Hand-check 50 random synthetic examples once, and report how often the "correct" answers really are correct.

### 10.2 Temperature `T`

Fit `T` on fit-split (claim, gold chunk) pairs using `nli_label`, by minimising negative log-likelihood.

### 10.3 Trust model

- `StandardScaler` + `LogisticRegression` (L2 penalty, C chosen by cross-validation).
- **No class weighting.** Re-weighting would make the probabilities wrong.
- **Data:** the synthetic fit split plus feedback examples (weight 3.0).
- **Refit:** after each document's synthetic set, and after every 10 feedback labels.
- **Promotion:** the new model goes live only if its test-split Brier score is no worse than the live model's.
- **Minimum data:** 20 examples of each class; otherwise the previous version stays.

### 10.4 Thresholds with a guarantee

Thresholds are chosen on the **cal** split, which is never used for `T` or the trust model:

- **`τ_accept`:** go through thresholds from strict to loose (0.99, 0.98, …, 0.50). At each one, compute the 95% Clopper-Pearson upper bound on the error rate of the answers it would accept. Keep loosening while the bound is ≤ `risk_alpha_accept` (5%), and **stop at the first failure**. Stopping at the first failure (fixed-sequence testing, as in Learn-then-Test) is what keeps the 95% confidence valid across many thresholds.
- **`τ_low`:** same procedure at `risk_alpha_low` (15%).
- **`τ_block`:** go from 0.99 downward. At each `t`, bound the share of *correct* answers that `contra ≥ t` would block; keep lowering while the bound is ≤ `risk_false_block` (2%), and stop at the first failure.
- **`τ_rel`:** the reranker score that best separates gold chunks from others (max F1). No guarantee for this one.

**Meaning:** *"On data like this dataset's calibration examples, at most 5% of accepted answers are wrong, with 95% confidence."* Synthetic questions are easier than real ones, so the golden set checks whether this holds on real questions. If no threshold meets a target, the previous version stays and the UI says so.

The risk targets are the only human-set numbers. They are policy, not tuning.

---

## 11. User experience

### 11.1 Flow

1. **Dataset:** create one (the NASA demo is preloaded).
2. **Upload:** drag in PDFs. Each shows live stages (parsing page 12/72 → embedding → indexing → ready), then its extraction report.
3. **Calibration:** runs automatically. The dataset badge changes from "Fallback thresholds" to "Calibrated · 5% risk target".
4. **Chat:** start a conversation and pick one document, or tick several for cross-document mode. Example question chips (covering text, tables, charts and images) come from the synthetic questions.
5. **Ask a series of questions:** each answer appears as a chat turn with its own decision banner, score card, coloured sentences and citation chips. Follow-ups ("what about the next table?") use the earlier turns.
6. **Inspect:** a chip opens the evidence card and the page preview with the evidence highlighted.
7. **Feedback:** thumbs up/down on each answer, with an optional reason ("wrong number", "missing info").

### 11.1a Score card (on every answer)

```text
✅ Verified · Trust 91        Claims: 2 supported / 2     Evidence: Table · p.36
Support 0.93 · Numbers ✓ · Quotes ✓ · Retrieval 0.84     Calibrated v1 (≤5% risk)
```

- **Trust (0–100):** the calibrated probability that the answer is correct.
- **Claims:** how many claims are supported, weak, unverified or contradicted.
- **Evidence type:** text, table, chart, KPI or image, so the user knows what the answer rests on. Image or chart answers say "based on AI reading of an image".
- **Checks:** lowest claim support, number match, quote match, top retrieval score.

The chat header shows running totals for the conversation, e.g. *6 questions · 4 verified · 1 partly · 1 withheld · average trust 84*.

### 11.2 Progress while answering

The server sends stage events over Server-Sent Events: *Searching → Reading 8 passages → Drafting → Checking claim 2 of 4 → Repairing → Done*. The answer appears only after verification.

### 11.3 Results panel

- **Banner:**
  - ACCEPT: green "Verified against 3 passages"
  - ACCEPT_LOW_CONFIDENCE: amber "Partly verified"
  - WARN: amber "Some statements not found in the source"
  - BLOCK: red "Answer withheld — it conflicted with the source"
  - NO_SUPPORT: grey "Not in these documents"
- **Answer:** each sentence underlined in its claim colour, with chips like `[1 · p.36]`. Hover shows the quote.
- **Evidence cards:** file, page, section, type icon, highlighted span. Tables render as tables; charts and photos show the image crop, with AI-read values or descriptions marked "derived".
- **Page preview:** the page rendered from the original PDF (pypdfium2) with the evidence box drawn on it.
- **Details** (collapsed): claim × passage scores, check results, trust score, calibration version.
- **BLOCK:** "The draft said *X*. Page 36 says *Y*." plus the evidence card.

### 11.4 Analytics page

- **Calibration card:** thresholds, guarantee, example counts, versions, Brier/ECE, reliability diagram.
- **Charts** (aggregated from `queries`): decision mix, latency, trust histogram, feedback rate.
- FEVER health card and query log.

### 11.5 Visual design

- **Colours:** `--bg #050505`, `--panel #0d0d0f`, `--panel2 #121214`, `--line #1d1d22`, `--text #f5f5f5`, `--muted #7a7a85`, `--red #ff003c`, `--green #00e676`, `--amber #ffb300`.
- **Type:** Inter for text; JetBrains Mono for scores and IDs.
- **Colour use:** red/amber/green appear only for verdicts, and always with an icon and a word, so they work for colour-blind users.
- **Layout:** three columns on desktop (library / question and answer / evidence); one column with an evidence drawer on mobile.

---

## 12. API

All routes are under `/api`. The built React app is served at `/`.

| Route | Purpose |
|---|---|
| `POST /api/datasets` · `GET /api/datasets` · `DELETE /api/datasets/{id}` | Datasets |
| `POST /api/datasets/{id}/documents` | Upload one or more PDFs |
| `GET /api/datasets/{id}/documents` | Library |
| `GET /api/documents/{id}` | Status, extraction report, outline |
| `GET /api/documents/{id}/pages/{n}.png?highlight=<chunk_id>` | Page image with highlight |
| `DELETE /api/documents/{id}` | Delete the document and everything derived from it, then refit |
| `POST /api/sessions` · `GET /api/sessions?dataset_id=` · `GET /api/sessions/{id}` | Start, list and open conversations (with all turns) |
| `POST /api/ask` | `{session_id, question}` (session holds dataset and documents) → SSE stage events, then the result with its score card |
| `GET /api/queries/{id}` | Full trace |
| `POST /api/queries/{id}/feedback` | `{value, reason?}` |
| `GET /api/datasets/{id}/calibration` · `POST /api/datasets/{id}/calibration/refit` | Calibration |
| `GET /api/analytics?dataset_id=` | Dashboard numbers |
| `GET /api/validation/fever` | Latest benchmark run |
| `GET /api/health` | Models loaded, database connected, indexes ready |

### 12.1 Answer output (`POST /api/ask`)

The stream first sends progress events such as `{"stage": "checking", "claim": 2, "of": 3}`. The last event is the result:

```json
{
  "query_id": "q_7f2c", "session_id": "s_19ab", "turn": 1,
  "question": "How long are research integrity case records kept?",
  "standalone_question": "How long are research integrity case records kept?",

  "decision": "ACCEPT",
  "trust": 91,
  "answer": "Records of research integrity complaints are destroyed 7 years after the case is closed, or 6 years after the agreed action is taken, whichever is later.",

  "claims": [
    { "text": "Records of research integrity complaints are destroyed 7 years after the case is closed.",
      "label": "SUPPORTED", "support": 0.93, "contra": 0.02,
      "cites": ["C1"], "quote": "Destroy 7 years after case is closed",
      "checks": { "quote_match": true, "numbers_ok": true, "derived_only": false },
      "highlight": { "chunk_id": "c_8b1e0f", "page": 36, "span": [88, 140] } }
  ],

  "evidence": [
    { "ref": "C1", "file_name": "nasa_scientific_integrity_policy.pdf", "page": 36, "type": "table",
      "section": "Table 2. Retaining documentation from SI cases",
      "text": "Records of complaints regarding research integrity ... Destroy 7 years after case is closed ...",
      "bbox": [0.08, 0.31, 0.92, 0.47], "rerank": 0.84 }
  ],

  "score_card": {
    "claims": { "supported": 2, "weak": 0, "unverified": 0, "contradicted": 0 },
    "evidence_types": ["table"],
    "min_support": 0.93, "numbers_ok": true, "quotes_ok": true,
    "top_retrieval": 0.84, "repaired": false,
    "calibration": { "version": 1, "risk_target": "≤5% wrong at 95% confidence" }
  },

  "blocked_reason": null,
  "session_summary": { "turns": 1, "ACCEPT": 1, "ACCEPT_LOW_CONFIDENCE": 0, "WARN": 0, "BLOCK": 0, "NO_SUPPORT": 0, "avg_trust": 91 },
  "latency_ms": { "retrieve": 420, "rerank": 610, "llm": 1900, "verify": 2300, "total": 5230 }
}
```

How the fields change by decision:

| Decision | Difference |
|---|---|
| ACCEPT_LOW_CONFIDENCE | Some claims are `WEAKLY_SUPPORTED` (e.g. `derived_only: true` for chart/image answers) |
| WARN | Some claims are `UNVERIFIED`; the UI marks those sentences |
| BLOCK | `answer` is empty; `blocked_reason` holds `{draft_claim, evidence_ref, evidence_text, page}` |
| NO_SUPPORT | `claims` is empty; `evidence` holds the closest passages |

---

## 13. FEVER benchmark check (offline)

- **Data:** `pietrolesci/nli_fever` (Parquet), dev split only (a few MB); the test split has no labels. Download it and make the sample with `scripts/download_fever.py` (Section 22.4). Don't download the raw `fever` dataset or Wikipedia.
  - **Caution:** its `premise` column holds the *claim* and `hypothesis` holds the *evidence*. `eval/fever_data.load_sample_pairs()` swaps them; always load pairs through it. Labels: 0 entailment, 1 neutral, 2 contradiction.
  - Balanced sample of 600 (200 per label, seed 42), saved in `data/fever/sample_ids.json`.
- **Script:** `scripts/run_fever_validation.py` scores those pairs with the NLI model. Rerun only when the NLI model changes.
- **Outputs:** accuracy, per-label precision/recall/F1, macro-F1, confusion matrix, latency per pair. Stored in `fever_validations` and shown on Analytics.
- **Interpretation:** the NLI model was trained on FEVER-NLI, so this is a health check, not an independent test. The golden set is the independent test.

---

## 14. Evaluation

### 14.1 Data

| Set | Size | Role |
|---|---|---|
| FEVER-NLI dev sample | 600 pairs | Verifier health check |
| Synthetic | ~30 chunks × 2.5 examples per document | Calibration; reported separately |
| **Golden set (NASA)** | 150 claims + 60 questions (12 unanswerable), handwritten, labelled by both teammates (Cohen's kappa) | Independent test |

Golden claims by type:

| Content type | Claims |
|---|---|
| Text | 60 |
| Tables | 30 |
| Charts | 15 |
| KPIs / numbers | 20 |
| Quotes | 15 |
| Multi-hop (2 passages or 2 documents) | 10 |

Of the 60 questions, 20 target tables or charts and 8 target photos/diagrams. 15 of the questions are follow-ups inside 5 short conversations, to test the rewrite step (correct standalone question and retrieval recall@5 on follow-ups vs first questions). Mutations follow FEVER (negation, entity swap, number change, generalisation, more specific, similar but wrong). The page-30 false positive from the original report is a fixed regression case.

### 14.2 Experiments

| # | Question | Compare | Metric |
|---|---|---|---|
| E0 | Does structure-aware extraction help? | pdfplumber + character chunks vs Docling + element chunks | Recall@5 and answer accuracy by content type |
| E1 | Which retrieval works best? | Vector vs keyword vs RRF vs RRF + reranker | Recall@5, MRR |
| E2 | Does claim splitting help? | Whole answer vs per claim | AUROC on injected hallucinations |
| E3 | What do the checks add? | NLI vs + quote vs + numbers | Detection F1, especially number swaps |
| E4 | What do the gate and repair buy? | No gate vs gate vs gate + repair | Hallucination rate shown, coverage, abstention on unanswerables |
| E5 | Do learned thresholds keep their promise? | Fixed 0.75/0.60 vs risk-controlled | Observed accepted-error vs 5% target, coverage |
| E6 | Does trust improve with feedback, and is the large model worth it? | ECE/Brier after 0–200 labels; DeBERTa large vs base | ECE, Brier, macro-F1, latency |

**Headline (from E4/E5):** *"Argus cuts hallucinated answers shown to users from X% to Y% while answering Z% of questions; the accepted-answer error rate was W% against a 5% target."*

Report the main numbers with bootstrap 95% confidence intervals.

---

## 15. Performance (2 vCPU estimates; measure in Week 2)

| Stage | Estimate |
|---|---|
| Ingestion | ~1–3 s per page (NASA set about 4–8 minutes, in the background) |
| Embed + two searches | 0.2–0.5 s |
| Rerank 30 | 0.6–1.2 s |
| LLM | 0.8–2 s |
| Verify 12–20 pairs (large model) | 2–5 s |
| **Total p50** | **~4–9 s**; repair adds one LLM call + verification |

If p50 is over 8 s, try these in order: export NLI and reranker to ONNX with int8 quantization (`optimum`), rerank 20 instead of 30, switch to the base NLI model.

Memory is about 5–6 GB for all models.

---

## 16. Deployment

- **App:** one container on a free Hugging Face Space (2 vCPU, 16 GB RAM, disk not persistent).
  - FastAPI on port 7860 serves `/api` and the React build.
  - The Docker build downloads all models, so a restart only loads them from disk.
- **Database:** a free MongoDB Atlas cluster in the same region (e.g. AWS us-east-1), holding all state including the PDFs.
- **Secrets:** `MONGO_URI` and `GROQ_API_KEY` in the Space settings.
- **Seed:** `scripts/seed_demo.py` creates the NASA dataset, ingests the 5 PDFs and calibrates.
- **Sleep:** free Spaces sleep when idle, so the first visit after that waits about a minute.
- **If Docker Spaces need a paid plan on your account:** use a Gradio-SDK Space whose `app.py` starts the same FastAPI app on port 7860.

---

## 17. Repository structure

```text
argus/
├── backend/
│   ├── main.py              # FastAPI app; /api + static frontend
│   ├── config.py            # settings and fallback values (pydantic-settings, reads .env)
│   ├── models.py            # loads BGE, reranker and NLI once; shared by everything
│   ├── pipeline.py          # run_question(): one question end to end; used by API, CLI, eval, calibration
│   ├── worker.py            # ingestion + calibration jobs
│   ├── common/              # text.py (normalise), numbers.py (parse/compare), ids.py
│   ├── api/                 # datasets, documents, sessions, ask (SSE), queries, calibration, analytics, health
│   ├── ingestion/           # intake, parse_docling, parse_plain, elements, tables, figures, chunking, enrich, report
│   ├── retrieval/           # embedder, atlas_search (vector + text), fusion, reranker, context
│   ├── generation/          # prompts, llm (JSON, fallback, cache), schemas
│   ├── verification/        # nli, checks, aggregate, gate, repair, features
│   ├── calibration/         # synthetic, temperature, trust_model, thresholds, registry
│   ├── db/                  # client, indexes (incl. search index definitions)
│   └── requirements.txt     # pinned
├── eval/                    # fever_data.py, run_eval.py, metrics.py, experiments/e0…e6
├── scripts/                 # check_setup.py, download_fever.py, run_fever_validation.py, seed_demo.py
├── data/                    # samples/, fever/, golden/, cache/ (layout in Section 22.2)
├── results/                 # committed eval outputs and figures
├── docs/                    # Argus Spec.md, reports/
├── frontend/                # Vite + React + Tailwind
├── tests/                   # test_<module>.py
├── Dockerfile · Makefile · .env.example · .gitignore · README.md
```

Cleanup of the current repo is in Section 22.1.

---

## 18. Configuration and dependencies

```text
MONGO_URI, DB_NAME=argus
GROQ_API_KEY
GROQ_MODELS=openai/gpt-oss-120b,openai/gpt-oss-20b     # main, then fallback
VISION_MODEL=qwen/qwen3.8-27b                          # charts and photos
HF_HOME=models/hf                                      # Hugging Face model cache
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
RERANKER_MODEL=BAAI/bge-reranker-base
NLI_MODEL_NAME=MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli
CHUNK_MAX_TOKENS=320, RETRIEVE_LIMIT=30, NUM_CANDIDATES=400, RERANK_KEEP=8, CONTEXT_MAX_TOKENS=3500
MAX_UPLOAD_MB=50, MAX_PAGES=500
SYNTHETIC_PER_DOC=30, FEEDBACK_WEIGHT=3.0, MIN_CLASS_EXAMPLES=20
FALLBACK_TAU_ACCEPT=0.75, FALLBACK_TAU_LOW=0.60, FALLBACK_TAU_BLOCK=0.75, FALLBACK_TAU_REL=0.0
```

**Groq models** (from your account's model list):
- `openai/gpt-oss-120b` is the main LLM (answers, repair, rewrite, synthetic questions), with `openai/gpt-oss-20b` as fallback.
- `qwen/qwen3.8-27b` is the only model listed that takes images.
- The gpt-oss models are reasoning models. Use `reasoning_effort="low"` for rewrite and synthetic calls, and `"medium"` for answers and repair.
- The other listed models (Whisper, Orpheus, prompt-guard, safeguard, Allam) are speech, safety or Arabic models and are not used.

- **Python:** fastapi, uvicorn, sse-starlette, pydantic, pydantic-settings, pymongo ≥ 4.10, python-dotenv, docling, pdfplumber, pypdfium2, pysbd, rapidfuzz, sentence-transformers, transformers, torch (CPU), numpy, scipy, scikit-learn, pandas, pyarrow, groq, datasets. Add optimum[onnxruntime] only if latency needs it.
- **Dev:** ruff, pytest.
- **Frontend:** react, react-router-dom, @tanstack/react-query, recharts, tailwindcss, lucide-react.

---

## 19. Build plan (6 weeks)

| Week | Build | Done when |
|---|---|---|
| 1 | **First Section 22** (cleanup, folders, `.gitignore`, FEVER download, `check_setup.py`); then Atlas cluster, collections, indexes; intake + GridFS; Docling parsing, tables, figures, chunking, numbers/quotes, embeddings; extraction report | All 5 NASA PDFs ingested; the report shows tables, charts and TOC handled as in 5.3 |
| 2 | Follow-up rewrite + sessions; hybrid retrieval, RRF, reranker, context; quote-anchored generation; NLI, checks, gate, repair; CLI `argus chat` | Per-claim verdicts with page citations from the CLI; latency measured |
| 3 | Synthetic examples, temperature, trust model, thresholds, registry; FEVER script; golden set written and labelled in parallel | Dataset "Calibrated v1"; kappa reported; FEVER run stored |
| 4 | FastAPI with SSE and worker; React: datasets, upload with live stages, chat with multiple turns, banner, score card, chips, evidence cards | Upload → ask → inspect works in the browser on a new dataset |
| 5 | Page preview with highlights, details panel, feedback, analytics; eval harness; experiments E0–E6 | `make eval` writes every result table with confidence intervals |
| 6 | Docker image, Hugging Face Space + Atlas, seed script, README with GIF and headline number, report | Public URL works end to end; report numbers match `results/` |

---

## 20. Contributions and limitations

**Contributions**
1. Structure-aware evidence for verification (tables as row facts, charts split into text-layer vs derived values), with its effect measured (E0, E3).
2. A quote-anchored, claim-level gate with number and quote checks, plus one verifier-guided repair.
3. Per-dataset thresholds that bound the error rate of accepted answers, checked on real questions.
4. Self-calibration from synthetic examples generated per dataset, refined by feedback.

**Limitations**
- The NLI model was trained on FEVER-NLI; the golden set is the independent test.
- Synthetic mutations are easier than real hallucinations. The guarantee assumes new questions resemble the calibration examples.
- Chart values read only from pixels depend on a vision model; they are marked derived and capped.
- NLI is sentence-level. Claims needing arithmetic across rows may come out UNVERIFIED.
- On free CPU hosting, an answer takes several seconds.

**Open decisions:** the risk target (5% proposed); whether chart and photo images may be sent to Groq; large vs base NLI model (after E6); Docker vs Gradio Space; who writes the golden set.

---

## 21. What to learn, and where

Learn each topic just before the week that needs it.

| Week | Topic | What you need to know | Resource |
|---|---|---|---|
| 1 | MongoDB data modelling | Embedding vs referencing, the 16 MB limit, the Extended Reference / Computed / Subset patterns | [MongoDB data modeling docs](https://www.mongodb.com/docs/manual/data-modeling/) · [MongoDB University (free courses)](https://learn.mongodb.com/) |
| 1 | Atlas Vector Search + Search | Vector index fields, filters, `$vectorSearch`, `$search`, hybrid search | [Vector index fields](https://www.mongodb.com/docs/vector-search/indexes/vector-search-type.md) · [Hybrid search](https://www.mongodb.com/docs/vector-search/hybrid-search/hybrid-search-overview.md) · [Limits](https://www.mongodb.com/docs/vector-search/deployment/compatibility-limitations.md) |
| 1 | Docling | Converter options, document structure, tables, pictures, HybridChunker | [Docling docs](https://docling-project.github.io/docling/) · [Chunking](https://docling-project.github.io/docling/concepts/chunking/) · [Enrichments](https://docling-project.github.io/docling/usage/enrichments/) · [Docling technical report](https://arxiv.org/abs/2408.09869) |
| 1 | Embeddings | BGE query instruction, normalisation, cosine similarity | [FlagEmbedding (BGE)](https://github.com/FlagOpen/FlagEmbedding) · [Sentence-Transformers](https://sbert.net/) |
| 2 | RAG basics | Retrieve → generate, why grounding fails | [Lewis et al., RAG (2020)](https://arxiv.org/abs/2005.11401) |
| 2 | Fusion + reranking | RRF formula, cross-encoders vs bi-encoders | [Cormack et al., RRF (2009)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf) · [Sentence-Transformers docs (Cross-Encoder section)](https://sbert.net/) |
| 2 | NLI for fact checking | Entailment / neutral / contradiction, chunk vs sentence premises, atomic claims | [FEVER (2018)](https://arxiv.org/abs/1803.05355) · [SummaC (2022)](https://arxiv.org/abs/2111.09525) · [FActScore (2023)](https://arxiv.org/abs/2305.14251) · [NLI model card](https://huggingface.co/MoritzLaurer/DeBERTa-v3-large-mnli-fever-anli-ling-wanli) |
| 2 | Groq API | Chat completions, JSON mode, vision input, rate limits | [Groq docs](https://console.groq.com/docs) · [Vision](https://console.groq.com/docs/vision) |
| 3 | Calibration | Temperature scaling, ECE, Brier score, reliability diagrams | [Guo et al., On Calibration (2017)](https://arxiv.org/abs/1706.04599) · [scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html) |
| 3 | Risk-controlled thresholds | Clopper-Pearson bounds, fixed-sequence testing | [Angelopoulos & Bates, Gentle Intro to Conformal Prediction](https://arxiv.org/abs/2107.07511) · [Learn then Test (2021)](https://arxiv.org/abs/2110.01052) |
| 3 | Annotation statistics | Cohen's kappa, bootstrap confidence intervals | [scikit-learn `cohen_kappa_score`](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html) · [SciPy `bootstrap`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html) |
| 4 | FastAPI | Routes, background tasks, file uploads, Server-Sent Events | [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/) · [sse-starlette](https://github.com/sysid/sse-starlette) |
| 4 | React frontend | Vite setup, data fetching with TanStack Query, Tailwind | [React docs](https://react.dev/learn) · [TanStack Query](https://tanstack.com/query/latest/docs/framework/react/overview) · [Tailwind CSS](https://tailwindcss.com/docs) |
| 6 | Deployment | Docker basics, Hugging Face Docker Spaces, secrets | [Docker get started](https://docs.docker.com/get-started/) · [HF Docker Spaces](https://huggingface.co/docs/hub/spaces-sdks-docker) |

---

## 22. Project setup, conventions and coding standards

Do 22.1–22.4 once, before the Week 1 build.

### 22.1 Clean up the current repo

| Current file or folder | Action | Why |
|---|---|---|
| `app.py`, `.streamlit/` | Delete | The Streamlit UI is replaced by React |
| `main.py`, `check_connect.py`, `scripts/build_index.py`, `scripts/test_retrieval.py`, `scripts/check_models.py` | Delete | Old FAISS pipeline and one-off checks |
| `llm_check.py`, `scripts/check_mongodb.py` | Merge into `scripts/check_setup.py` | One script checks MongoDB, Groq models and the Atlas indexes |
| `src/` | Keep until Week 1 has ported what is reused (PDF loader, prompt template), then delete | Git history keeps the old code |
| `data/embeddings/` | Delete | FAISS is replaced by Atlas Vector Search |
| `logs/` (74 JSON files) | Delete and untrack | Query traces now live in the `queries` collection |
| `data/raw_documents/nasa/*.pdf` | Move to `data/samples/nasa/` | Demo and test dataset; committed (US government works) |
| `data/raw_documents/anime/` | Move to `data/samples/anime/`; delete its duplicate ISS PDF | Second dataset for testing "upload your own dataset"; kept local only |
| `ARGUS NLP Project Report.pdf` | Move to `docs/reports/argus_v1_report.pdf` | Keeps the root clean |
| `requirements.txt` (empty) | Delete | Replaced by `backend/requirements.txt` |
| `.gitignore` | Replace with 22.3 | The old one ignores all of `data/`, which would block the golden set |

After moving the files and replacing `.gitignore`, untrack what is now ignored and commit:

```bash
git rm -r --cached --quiet logs data
git add -A
git status            # check: no PDFs except data/samples/nasa, no logs, no .env
git commit -m "Clean repo: new layout and .gitignore"
```

`.env` has never been committed (checked with `git log --all -- .env`), so the keys don't need rotating.

### 22.2 Folder layout and naming

```text
data/
├── samples/
│   ├── nasa/                     # demo + test PDFs (committed)
│   └── anime/                    # second test dataset (local only)
├── fever/
│   ├── nli_fever_dev.parquet     # downloaded (ignored)
│   └── sample_ids.json           # fixed 600-row sample (committed)
├── golden/
│   ├── claims.jsonl              # hand-written test claims (committed)
│   ├── questions.jsonl
│   └── annotation_guide.md
├── cache/llm/                    # LLM responses by prompt hash (ignored)
└── uploads/                      # temporary local uploads (ignored)
models/hf/                        # Hugging Face model cache, HF_HOME (ignored)
results/<experiment>/<run_id>.json  # eval outputs (committed)
results/figures/<name>.png
docs/Argus Spec.md · docs/reports/
```

| Thing | Convention | Example |
|---|---|---|
| Files, folders, Python modules | lowercase `snake_case` | `parse_docling.py`, `nasa_scientific_integrity_policy.pdf` |
| Python classes | `PascalCase` | `ChunkRecord` |
| Functions, variables | `snake_case` | `load_sample_pairs` |
| Constants, environment variables | `UPPER_SNAKE` | `PER_LABEL`, `MONGO_URI` |
| React components | `PascalCase.jsx`, one per file | `ScoreCard.jsx` |
| React hooks | `useThing.js` | `useAsk.js` |
| MongoDB collections and fields | `snake_case`; collections plural | `calibration_examples.document_id` |
| Record IDs | Type prefix + `_` | `ds_`, `doc_`, `c_`, `a_`, `s_`, `q_` |
| Downloaded datasets | `<source>_<split>.<ext>` | `nli_fever_dev.parquet` |
| Experiment runs | `<exp>_<YYYY-MM-DD>_<nn>.json` | `e1_2026-11-02_01.json` |
| Git branches / commits | `type/short-name`; imperative message | `feat/ingestion`; "Add RRF fusion" |

### 22.3 `.gitignore`

Replace the current file with this one. Each rule was tested with `git check-ignore`: the golden set, `sample_ids.json`, the NASA PDFs, results and `.env.example` are tracked; everything else here is ignored.

```gitignore
# Python
__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.mypy_cache/
*.egg-info/

# Environments and secrets
venv/
.venv/
.env
.env.*
!.env.example

# Frontend
frontend/node_modules/
frontend/dist/

# Models and caches (Hugging Face downloads go to models/hf)
models/
.cache/

# Data: ignore downloads, uploads and caches; keep small hand-made files
data/fever/*
!data/fever/sample_ids.json
data/samples/*
!data/samples/nasa/
data/cache/
data/uploads/

# Generated output
logs/
results/tmp/
*.log

# OS and editors
.DS_Store
Thumbs.db
.vscode/
.idea/
```

### 22.4 Download FEVER-NLI

Create empty `eval/__init__.py` and `scripts/__init__.py`, add the two files below, then run from the repo root:

```bash
python -m scripts.download_fever
```

The first run downloads the dev split (a few MB) to `data/fever/nli_fever_dev.parquet` and writes `data/fever/sample_ids.json`. Later runs reuse both. Commit `sample_ids.json`.

`eval/fever_data.py`, the only place that reads FEVER data:

```python
"""FEVER-NLI data: download once, fixed balanced sample, and pairs ready for the NLI check."""

import json
from pathlib import Path

import pandas as pd
from datasets import load_dataset

HF_DATASET = "pietrolesci/nli_fever"
FEVER_DIR = Path("data/fever")
DEV_FILE = FEVER_DIR / "nli_fever_dev.parquet"
SAMPLE_FILE = FEVER_DIR / "sample_ids.json"
PER_LABEL = 200  # 3 labels x 200 = 600 pairs
SEED = 42
LABELS = {0: "entailment", 1: "neutral", 2: "contradiction"}


def load_dev() -> pd.DataFrame:
    """Return the dev split, downloading it only the first time."""
    if not DEV_FILE.exists():
        FEVER_DIR.mkdir(parents=True, exist_ok=True)
        load_dataset(HF_DATASET, split="dev").to_parquet(str(DEV_FILE))
    return pd.read_parquet(DEV_FILE)


def make_sample(dev: pd.DataFrame) -> list[int]:
    """Pick PER_LABEL rows per label with a fixed seed and save their row numbers."""
    rows = dev.groupby("label").sample(n=PER_LABEL, random_state=SEED).index
    ids = sorted(int(i) for i in rows)
    meta = {"seed": SEED, "per_label": PER_LABEL, "rows": ids}
    SAMPLE_FILE.write_text(json.dumps(meta, indent=2))
    return ids


def load_sample_pairs() -> pd.DataFrame:
    """Sampled pairs as premise=evidence, hypothesis=claim."""
    sample = load_dev().loc[json.loads(SAMPLE_FILE.read_text())["rows"]]
    # The dataset stores the claim in "premise" and the evidence in "hypothesis", so swap them.
    return pd.DataFrame(
        {
            "premise": sample["hypothesis"],
            "hypothesis": sample["premise"],
            "label": sample["label"].map(LABELS),
        }
    ).reset_index(names="row")
```

`scripts/download_fever.py`:

```python
"""One-time setup: download FEVER-NLI dev and create the fixed 600-pair sample.

Run from the repo root: python -m scripts.download_fever
"""

from eval.fever_data import SAMPLE_FILE, load_dev, make_sample


def main() -> None:
    dev = load_dev()
    if SAMPLE_FILE.exists():
        status = "kept existing"  # reuse it so results stay comparable across runs
    else:
        status = f"created ({len(make_sample(dev))} rows)"
    print(f"dev rows: {len(dev)} | sample {SAMPLE_FILE}: {status}")


if __name__ == "__main__":
    main()
```

`scripts/run_fever_validation.py` (Week 3) calls `load_sample_pairs()` and the shared NLI model from `backend/models.py`. It doesn't read the parquet itself.

### 22.5 Coding standards

**Tooling:** Python 3.11; `ruff format` and `ruff check` (line length 100); type hints on public functions; `pytest`.

**Structure:**
- One job per module; keep functions short (about 40 lines at most).
- No magic numbers in code. Every tunable value is in `backend/config.py` (pydantic-settings, read from `.env`).

**Don't repeat logic. Each shared job has exactly one home:**

| Job | Only place | Used by |
|---|---|---|
| Settings | `backend/config.py` | Everything |
| MongoDB client and collections | `backend/db/client.py` | Everything |
| Loading BGE, reranker, NLI (once, cached) | `backend/models.py` | Retrieval, verification, calibration, FEVER |
| Every Groq call (JSON mode, fallback, cache, vision) | `backend/generation/llm.py` | Answers, repair, rewrite, synthetic questions, image reading |
| Text normalisation | `backend/common/text.py` | Chunking, quote check, search text |
| Number parsing and comparison | `backend/common/numbers.py` | Enrichment, number check, synthetic number swaps |
| ID creation | `backend/common/ids.py` | Ingestion, sessions, queries |
| One question end to end | `backend/pipeline.py` `run_question()` | API, CLI, eval harness, calibration examples |
| FEVER data | `eval/fever_data.py` | Download and validation scripts |

**Comments:**
- A one-line docstring on each module and public function.
- Inline comments only to explain *why*, in one or two lines.
- No commented-out code, no banner comments, no long comment blocks.

**Errors and logging:**
- No bare `except`. Raise clear errors at boundaries (API input, database, LLM).
- Use `logging`, not `print`. Scripts may print their final result.

**Tests:**
- `tests/test_<module>.py`, with no network in unit tests (fake LLM and database).
- Every bug fix adds a test.

**Frontend:**
- API calls only in `src/api/client.js`.
- Colours only from the tokens in 11.5.
- One component per file.

**Reference:** the code in 22.4 shows the expected style: short functions, constants at the top, one-line docstrings, and a single *why* comment where it's needed.

