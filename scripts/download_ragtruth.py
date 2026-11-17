"""Download a fixed RAGTruth subset (~1500 answers) for trust model fitting.

Uses wandb/RAGTruth-processed (public, no token needed).
Data is cached under data/ragtruth/ (git-ignored).

Run from the repo root:
    python -m scripts.download_ragtruth
"""

import json
import logging
import random

from datasets import load_dataset

from backend.config import ROOT_DIR

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

OUT_DIR = ROOT_DIR / "data" / "ragtruth"
CACHE_FILE = OUT_DIR / "ragtruth_subset.json"
SEED = 42
TARGET_N = 1500


def main() -> None:
    if CACHE_FILE.exists():
        rows = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        log.info("Already downloaded: %d answers in %s", len(rows), CACHE_FILE)
        _stats(rows)
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log.info("Downloading RAGTruth-processed from HuggingFace...")

    ds = load_dataset("wandb/RAGTruth-processed", split="train")
    log.info("Full dataset: %d rows", len(ds))

    # Map to common schema: source_context, response, hallucination_spans
    rows = []
    for row in ds:
        labels = row.get("hallucination_labels", "[]")
        if isinstance(labels, str):
            try:
                spans = json.loads(labels)
            except (json.JSONDecodeError, TypeError):
                spans = []
        else:
            spans = labels if labels else []

        rows.append({
            "source_context": row["context"],
            "response": row["output"],
            "hallucination_spans": spans,
            "task_type": row.get("task_type", ""),
            "source_id": row.get("id", ""),
        })

    # Sample a fixed subset, stratified by faithful/hallucinated
    rng = random.Random(SEED)
    faithful = [r for r in rows if not r["hallucination_spans"]]
    hallucinated = [r for r in rows if r["hallucination_spans"]]
    log.info("Full set: %d faithful, %d hallucinated", len(faithful), len(hallucinated))

    # Take proportional sample up to TARGET_N
    total = len(rows)
    n_faithful = round(TARGET_N * len(faithful) / total)
    n_hallucinated = TARGET_N - n_faithful
    sample = rng.sample(faithful, min(n_faithful, len(faithful))) + rng.sample(
        hallucinated, min(n_hallucinated, len(hallucinated))
    )
    rng.shuffle(sample)

    CACHE_FILE.write_text(json.dumps(sample, indent=2), encoding="utf-8")
    log.info("Saved %d answers to %s", len(sample), CACHE_FILE)
    _stats(sample)


def _stats(rows: list[dict]) -> None:
    faithful = sum(1 for r in rows if not r["hallucination_spans"])
    print(f"  faithful: {faithful}, hallucinated: {len(rows) - faithful}")


if __name__ == "__main__":
    main()
