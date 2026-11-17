"""FEVER-NLI data: download once, fixed balanced sample, and pairs ready for the NLI check."""

import json
from pathlib import Path

import pandas as pd
from datasets import load_dataset

HF_DATASET = "pietrolesci/nli_fever"
FEVER_DIR = Path(__file__).resolve().parents[1] / "data" / "fever"
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
