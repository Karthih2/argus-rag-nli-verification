# Golden set (not written yet)

A hand-written, hand-labelled test set for the NASA documents, kept for later. When it exists:

- `questions.jsonl`: one question per line with `question`, `expected_answer`, `gold_chunk_ids`,
  `content_type` (text, table, figure caption) and `answerable`.
- `claims.jsonl`: one claim per line with `claim`, `gold_chunk_id` and `label`
  (SUPPORTED, CONTRADICTED or UNVERIFIED), labelled by two people (report Cohen's kappa).

Until then, `python -m eval.run --all` tests on RAGTruth (human labels) and on questions and
mutations generated from the ingested chunks.
