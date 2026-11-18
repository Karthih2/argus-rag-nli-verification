"""RAGTruth answers run through the live verifier: sentence claims with human labels + answer features.

Shared by scripts/fit_trust.py (fitting) and eval/run.py (testing), so both see identical data.
Each context is split into passages the way live chunks are sized, and each sentence cites the
passage closest to it (as the LLM cites a chunk live), so features mean the same thing live.
"""

import hashlib
import json
import logging

from rapidfuzz import fuzz

from backend.calibration.trust_model import FALLBACK_THRESHOLDS
from backend.common.text import sentence_spans, split_passages
from backend.config import ROOT_DIR, settings
from backend.generation.schemas import Claim
from backend.verification.features import extract_features
from backend.verification.gate import verify_claims

log = logging.getLogger(__name__)

RAGTRUTH_FILE = ROOT_DIR / "data" / "ragtruth" / "ragtruth_subset.json"
CACHE_FILE = ROOT_DIR / "data" / "cache" / "ragtruth_verified.json"
SEED = 42


def load_rows(limit: int | None = None) -> list[dict]:
    """The fixed RAGTruth subset (run scripts.download_ragtruth first)."""
    if not RAGTRUTH_FILE.exists():
        raise FileNotFoundError("RAGTruth data missing. Run: python -m scripts.download_ragtruth")
    rows = json.loads(RAGTRUTH_FILE.read_text(encoding="utf-8"))
    return rows[:limit] if limit else rows


def sentence_claims(response: str, spans: list[dict]) -> list[tuple[str, bool]]:
    """(sentence, faithful) for each sentence; unfaithful if it overlaps a labelled hallucination."""
    out = []
    for start, end in sentence_spans(response):
        bad = any(s["start"] < end and start < s["end"] for s in spans)
        out.append((response[start:end].strip(), not bad))
    return out


def verify_row(row: dict, temperature: float) -> dict | None:
    """One RAGTruth answer through verify_claims: per-claim scores + labels, answer features."""
    labelled = sentence_claims(row["response"], row["hallucination_spans"])
    passages = split_passages(row["source_context"], settings.CHUNK_MAX_TOKENS)
    if not labelled or not passages:
        return None
    evidence = [
        {"_id": f"p{i}", "_ref": f"C{i + 1}", "_rerank_score": 1.0, "text": p, "element_type": "text"}
        for i, p in enumerate(passages)
    ]
    claims = []
    for text, _ in labelled:
        closest = max(evidence, key=lambda e: fuzz.token_set_ratio(text, e["text"]))
        claims.append(Claim(text=text, cites=[closest["_ref"]]))
    verified = verify_claims(claims, evidence, temperature, FALLBACK_THRESHOLDS)
    return {
        "group": hashlib.sha1(row["source_context"].encode()).hexdigest()[:16],
        "faithful": not row["hallucination_spans"],
        "task_type": row.get("task_type", ""),
        "claims": [
            {"support": c["support"], "contra": c["contra"], "numbers_ok": c["checks"]["numbers_ok"], "faithful": ok}
            for c, (_, ok) in zip(verified, labelled)
        ],
        "features": extract_features(verified),
    }


def verified_examples(temperature: float, limit: int | None = None, refresh: bool = False) -> list[dict]:
    """All rows verified, cached per (NLI model, temperature, limit) because NLI over them is slow."""
    key = {"nli_model": settings.NLI_MODEL_NAME, "temperature": round(temperature, 4), "limit": limit,
           "windows": settings.NLI_WINDOWS_PER_CLAIM, "chunk_tokens": settings.CHUNK_MAX_TOKENS}
    if CACHE_FILE.exists() and not refresh:
        cached = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        if cached.get("key") == key:
            return cached["examples"]
    rows = load_rows(limit)
    examples = []
    for i, row in enumerate(rows, 1):
        ex = verify_row(row, temperature)
        if ex:
            examples.append(ex)
        if i % 100 == 0:
            log.info("RAGTruth verified %d / %d", i, len(rows))
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps({"key": key, "examples": examples}), encoding="utf-8")
    return examples


def split_groups(examples: list[dict]) -> dict[str, list[dict]]:
    """fit 60% / cal 20% / test 20%, by source context (no context in two splits), fixed seed."""
    from sklearn.model_selection import GroupShuffleSplit

    groups = [e["group"] for e in examples]
    idx = list(range(len(examples)))
    fit, rest = next(GroupShuffleSplit(1, test_size=0.4, random_state=SEED).split(idx, groups=groups))
    rest_groups = [groups[i] for i in rest]
    cal, test = next(GroupShuffleSplit(1, test_size=0.5, random_state=SEED).split(rest, groups=rest_groups))
    pick = lambda ids: [examples[i] for i in ids]  # noqa: E731
    return {"fit": pick(fit), "cal": pick(rest[cal]), "test": pick(rest[test])}
