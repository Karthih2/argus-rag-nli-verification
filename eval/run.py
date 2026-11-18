"""Evaluation runner, separate from the app.

    python -m eval.run --all
    python -m eval.run --hallucination --calibration --injected --retrieval --e2e

Writes results/<test>_<date>.json for each test and results/REPORT.md for the run.
LLM responses are cached (data/cache/llm) so reruns are repeatable.
"""

import argparse
import json
import logging
import random
import re
from collections import Counter
from datetime import datetime, timezone

import numpy as np

from backend.config import ROOT_DIR, settings

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

RESULTS_DIR = ROOT_DIR / "results"
SEED = 42
N_CHUNKS = 100
N_E2E = 50
UNANSWERABLE = [
    "What is the capital city of Peru?",
    "Who won the 1998 FIFA World Cup?",
    "What is the boiling point of ethanol in Fahrenheit?",
    "How many strings does a standard violin have?",
    "Which company makes the PlayStation console?",
    "What is the recipe for French onion soup?",
    "Who wrote the novel Pride and Prejudice?",
    "What is the population of Iceland?",
    "How tall is Mount Kilimanjaro?",
    "What is the exchange rate of the euro to the yen?",
]


# ----------------------------------------------------------------- shared helpers


def _ragtruth_test():
    from backend.calibration.trust_model import get_temperature, load_trust_json
    from eval.ragtruth import split_groups, verified_examples

    data = load_trust_json()
    if not data or "trust_model" not in data:
        raise RuntimeError("No fitted trust model. Run: python -m scripts.fit_trust")
    return split_groups(verified_examples(get_temperature()))["test"], data["trust_model"]


def _trust_probs(examples, model) -> np.ndarray:
    X = np.array([[e["features"].get(k, 0.0) for k in model["features"]] for e in examples], dtype=float)
    z = (X - np.array(model["mean"])) / np.array(model["scale"])
    return 1 / (1 + np.exp(-(z @ np.array(model["coef"]) + model["intercept"])))


def _sample_chunks(n: int, min_chars: int, dataset_id: str | None) -> list[dict]:
    from backend.db.client import chunks

    match = {"element_type": "text", **({"dataset_id": dataset_id} if dataset_id else {})}
    pool = [c for c in chunks().find(match, {"embedding": 0}).limit(2000) if len(c["text"]) >= min_chars]
    if len(pool) < 20:
        raise RuntimeError("Not enough text chunks; ingest documents first (python -m scripts.seed_demo)")
    return random.Random(SEED).sample(pool, min(n, len(pool)))


def _ask_llm(prompt: str) -> str:
    from backend.generation.llm import call_llm

    return call_llm([{"role": "user", "content": prompt}], json_mode=False, reasoning_effort="low").strip()


def _question_for(chunk: dict) -> str:
    return _ask_llm("Write ONE short factual question that this passage answers. Return ONLY the question.\n\n"
                    f"Passage: {chunk['text'][:800]}")


# ----------------------------------------------------------------- 1-2. RAGTruth (held-out test split)


def run_hallucination() -> dict:
    """Answer-level hallucination detection with the trust score on unseen RAGTruth contexts."""
    from sklearn.metrics import confusion_matrix, precision_recall_fscore_support, roc_auc_score

    test, model = _ragtruth_test()
    y = np.array([e["faithful"] for e in test], dtype=int)
    p = _trust_probs(test, model)
    pred = (p >= 0.5).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(y, pred, labels=[0, 1], zero_division=0)
    return {"n_test": len(test), "auroc": round(float(roc_auc_score(y, p)), 4),
            "hallucinated": {"precision": round(prec[0], 4), "recall": round(rec[0], 4), "f1": round(f1[0], 4)},
            "faithful": {"precision": round(prec[1], 4), "recall": round(rec[1], 4), "f1": round(f1[1], 4)},
            "confusion_matrix_rows_gold_hall_faith": confusion_matrix(y, pred, labels=[0, 1]).tolist()}


def run_calibration() -> dict:
    """Trust calibration (Brier, ECE, reliability) and the claim threshold's error on the test split."""
    from sklearn.metrics import brier_score_loss

    from backend.calibration.thresholds import clopper_pearson_upper
    from backend.calibration.trust_model import get_nli_thresholds
    from eval.metrics import ece, reliability

    test, model = _ragtruth_test()
    y = np.array([e["faithful"] for e in test], dtype=int)
    p = _trust_probs(test, model)
    tau = get_nli_thresholds()["tau_accept"]
    claims = [c for e in test for c in e["claims"]]
    accepted = [c for c in claims if c["support"] >= tau]
    errors = sum(not c["faithful"] for c in accepted)
    return {"n_test": len(test), "brier": round(float(brier_score_loss(y, p)), 4), "ece": round(ece(p, y), 4),
            "reliability": reliability(p, y), "tau_accept": tau, "claims": len(claims), "accepted": len(accepted),
            "accepted_error": round(errors / len(accepted), 4) if accepted else None,
            "accepted_error_upper95": round(clopper_pearson_upper(errors, len(accepted)), 4),
            "risk_target": settings.RISK_VERIFIED}


# ----------------------------------------------------------------- 3. Injected errors


def _number_swap(text: str) -> str:
    m = re.search(r"\d+(?:\.\d+)?", text)
    if not m:
        return ""
    value = float(m.group())
    new = value * 2 + 7 if value else 42
    return text[: m.start()] + (str(int(new)) if "." not in m.group() else f"{new:g}") + text[m.end():]


def _entity_swap(text: str, pool: list[str], rng: random.Random) -> str:
    words = text.split()
    caps = [i for i, w in enumerate(words) if i > 0 and w[:1].isupper() and w.isalpha() and len(w) > 2]
    if not caps:
        return ""
    i = caps[0]
    choices = [w for w in pool if w != words[i]]
    if not choices:
        return ""
    words[i] = rng.choice(choices)
    return " ".join(words)


def run_injected(dataset_id: str | None = None) -> dict:
    """Correct chunk sentences vs number / entity / negation versions, through the live verifier.

    Each mutated claim keeps the original sentence as its quote, as a model that copies the right
    quote but states the fact wrongly would.
    """
    from backend.calibration.trust_model import get_nli_thresholds, get_temperature
    from backend.common.text import sentences
    from backend.generation.schemas import Claim
    from backend.verification.gate import verify_claims

    rng = random.Random(SEED)
    sample = _sample_chunks(N_CHUNKS, 80, dataset_id)
    pool = sorted({w for c in sample for w in c["text"].split() if w[:1].isupper() and w.isalpha() and len(w) > 3})
    temperature, thresholds = get_temperature(), get_nli_thresholds()
    out: dict[str, list[str]] = {"correct": [], "number_swap": [], "entity_swap": [], "negation": []}
    for i, chunk in enumerate(sample):
        sent = next((s for s in sentences(chunk["text"]) if len(s) > 40), "")
        if not sent:
            continue
        evidence = [{**chunk, "_ref": "C1", "_rerank_score": 1.0}]
        variants = {"correct": sent, "number_swap": _number_swap(sent), "entity_swap": _entity_swap(sent, pool, rng)}
        if i < 30:
            variants["negation"] = _ask_llm(
                f"Rewrite this sentence so it states the opposite. Return ONLY the sentence.\n\n{sent}"
            )
        for kind, text in variants.items():
            if text and text != sent or kind == "correct":
                claim = Claim(text=text, cites=["C1"], quote=sent)
                out[kind].append(verify_claims([claim], evidence, temperature, thresholds)[0]["label"])

    def summary(labels):
        return {"n": len(labels), "counts": dict(Counter(labels)),
                "not_supported": round(sum(lb != "SUPPORTED" for lb in labels) / len(labels), 4) if labels else None,
                "contradicted": round(labels.count("CONTRADICTED") / len(labels), 4) if labels else None}

    result = {k: summary(v) for k, v in out.items()}
    result["false_alarm_rate"] = result["correct"]["not_supported"]
    return result


# ----------------------------------------------------------------- 4. Retrieval


def run_retrieval(dataset_id: str | None = None) -> dict:
    """Recall@5 and MRR for vector, keyword, and RRF + rerank, on LLM-written questions with a gold chunk."""
    from backend.retrieval.atlas_search import text_search, vector_search
    from backend.retrieval.fusion import rrf_fuse
    from backend.retrieval.reranker import rerank

    def score(hits, gold):
        ids = [h["_id"] for h in hits[:5]]
        return (1, 1 / (ids.index(gold) + 1)) if gold in ids else (0, 0.0)

    res = {"vector": [], "keyword": [], "hybrid_rerank": []}
    for chunk in _sample_chunks(N_CHUNKS, 100, dataset_id):
        q, ds, gold = _question_for(chunk), chunk["dataset_id"], chunk["_id"]
        vec, txt = vector_search(q, ds), text_search(q, ds)
        res["vector"].append(score(vec, gold))
        res["keyword"].append(score(txt, gold))
        res["hybrid_rerank"].append(score(rerank(q, rrf_fuse(vec, txt)), gold))
    return {k: {"n": len(v), "recall_at_5": round(float(np.mean([r for r, _ in v])), 4),
                "mrr": round(float(np.mean([m for _, m in v])), 4)} for k, v in res.items()}


# ----------------------------------------------------------------- 5. End to end


def run_e2e(dataset_id: str | None = None) -> dict:
    """Full pipeline on answerable questions (from chunks) and unanswerable ones (off-topic)."""
    from backend.pipeline import answer_and_verify, retrieve
    from eval.metrics import mean_ci

    sample = _sample_chunks(N_E2E, 100, dataset_id)
    ds = sample[0]["dataset_id"]

    failed = []

    def run(questions):
        rows = []
        for q in questions:
            try:
                checked = answer_and_verify(q, retrieve(q, ds))
            except RuntimeError as e:  # e.g. Groq still rate-limited after its retries: skip this one
                failed.append({"question": q, "error": str(e)})
                continue
            rows.append({"question": q, "decision": checked["decision"], "trust": checked["trust"]})
        return rows

    questions = []
    for chunk in sample:
        try:
            questions.append(_question_for(chunk))
        except RuntimeError as e:
            failed.append({"chunk": chunk["_id"], "error": str(e)})
    answerable = run(questions)
    unanswerable = run(UNANSWERABLE)
    if not answerable:
        raise RuntimeError(f"every question failed, e.g. {failed[:1]}")
    shown = lambda r: r["decision"] in ("ACCEPT", "ACCEPT_LOW_CONFIDENCE")  # noqa: E731
    trusts = [r["trust"] for r in answerable if r["trust"] is not None]
    return {
        "dataset_id": ds,
        "answerable": {"n": len(answerable), "decisions": dict(Counter(r["decision"] for r in answerable)),
                       "verified_or_partly": mean_ci([shown(r) for r in answerable]),
                       "missed_as_not_found": mean_ci([r["decision"] == "NO_SUPPORT" for r in answerable]),
                       "avg_trust": round(float(np.mean(trusts)), 1) if trusts else None},
        "unanswerable": {"n": len(unanswerable), "decisions": dict(Counter(r["decision"] for r in unanswerable)),
                         "correctly_not_answered": mean_ci([not shown(r) for r in unanswerable])},
        "failed_calls": len(failed),
    }


# ----------------------------------------------------------------- CLI

TESTS = {"hallucination": run_hallucination, "calibration": run_calibration, "injected": run_injected,
         "retrieval": run_retrieval, "e2e": run_e2e}
NEEDS_DATASET = {"injected", "retrieval", "e2e"}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--dataset", default="ds_nasa", help="dataset for the injected, retrieval and e2e tests")
    for name in TESTS:
        parser.add_argument(f"--{name}", action="store_true")
    args = parser.parse_args()
    chosen = [n for n in TESTS if args.all or getattr(args, n)]
    if not chosen:
        parser.error("choose --all or at least one test")

    settings.LLM_CACHE = True  # repeatable runs
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M")
    RESULTS_DIR.mkdir(exist_ok=True)
    results = {}
    for name in chosen:
        log.info("Running %s", name)
        try:
            results[name] = TESTS[name](args.dataset) if name in NEEDS_DATASET else TESTS[name]()
        except (RuntimeError, FileNotFoundError) as e:
            log.error("%s skipped: %s", name, e)
            results[name] = {"skipped": str(e)}
        (RESULTS_DIR / f"{name}_{stamp}.json").write_text(json.dumps(results[name], indent=2, default=str))
    report = [f"# Argus evaluation, {stamp} UTC\n", f"NLI model: `{settings.NLI_MODEL_NAME}`\n"]
    for name, res in results.items():
        report.append(f"## {name}\n\n```json\n{json.dumps(res, indent=2, default=str)}\n```\n")
    (RESULTS_DIR / "REPORT.md").write_text("\n".join(report), encoding="utf-8")
    print(f"Wrote {len(results)} result files and results/REPORT.md")


if __name__ == "__main__":
    main()
