"""Evaluation runner.

Usage:
    python -m eval.run --all                # run every test
    python -m eval.run --hallucination      # individual tests
    python -m eval.run --calibration
    python -m eval.run --injected
    python -m eval.run --retrieval
    python -m eval.run --e2e

Writes results/<name>_<date>.json per test and results/REPORT.md summary.
"""

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

import numpy as np

from backend.config import ROOT_DIR

logging.basicConfig(
    level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger(__name__)

RESULTS_DIR = ROOT_DIR / "results"
RAGTRUTH_FILE = ROOT_DIR / "data" / "ragtruth" / "ragtruth_subset.json"
TRUST_JSON = ROOT_DIR / "backend" / "calibration" / "trust.json"
SEED = 42


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _save(name: str, data: dict):
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = RESULTS_DIR / f"{name}_{_now()}.json"
    path.write_text(
        json.dumps(data, indent=2, default=str), encoding="utf-8"
    )
    log.info("Saved %s", path)
    return path


def _make_evidence(ctx_text: str, chunk_id: str = "ctx"):
    """Single-chunk fake evidence for RAGTruth evaluation."""
    return [{
        "_id": chunk_id,
        "_ref": "[1]",
        "_rerank_score": 1.0,
        "text": ctx_text[:4000],
        "element_type": "text",
    }]


def _process_ragtruth(trust_data: dict):
    """Process RAGTruth through NLI, return (X, y, groups).

    Shared by hallucination and calibration tests.
    """
    import pysbd

    from backend.calibration.trust_model import FALLBACK_NLI_THRESHOLDS
    from backend.generation.schemas import Claim
    from backend.verification.gate import verify_claims

    rows = json.loads(RAGTRUTH_FILE.read_text(encoding="utf-8"))
    temperature = trust_data["temperature"]
    thresholds = FALLBACK_NLI_THRESHOLDS
    segmenter = pysbd.Segmenter(language="en", clean=False)
    feature_keys = trust_data["trust_model"]["features"]

    X_rows, y_list, groups = [], [], []
    for i, row in enumerate(rows):
        response = row["response"]
        faithful = not row["hallucination_spans"]
        sentences = [
            s.strip() for s in segmenter.segment(response) if s.strip()
        ]
        if not sentences:
            continue
        claims = [
            Claim(text=s, cites=["[1]"], quote="") for s in sentences
        ]
        evidence = _make_evidence(row["source_context"])
        try:
            verified = verify_claims(
                claims, evidence, temperature, thresholds
            )
        except (ValueError, RuntimeError, KeyError):
            continue
        n = len(verified)
        supports = [c["support"] for c in verified]
        features = {
            "min_support": min(supports),
            "mean_support": sum(supports) / n,
            "max_rel_contra": max(c["contra"] for c in verified),
            "share_supported": (
                sum(c["label"] == "SUPPORTED" for c in verified) / n
            ),
            "n_claims": n,
            "quote_match_rate": 0.0,
            "number_mismatches": sum(
                not c["checks"]["numbers_ok"] for c in verified
            ),
            "top1_rerank": 1.0,
            "rerank_gap": 0.0,
            "repaired": 0,
        }
        X_rows.append([features[k] for k in feature_keys])
        y_list.append(1 if faithful else 0)
        groups.append(row.get("source_id", str(i)))
        if (i + 1) % 200 == 0:
            log.info("  processed %d / %d", i + 1, len(rows))

    return np.array(X_rows), np.array(y_list), groups


def _test_split(X, y, groups):
    """60/20/20 grouped split, return test indices."""
    from sklearn.model_selection import GroupShuffleSplit

    gss1 = GroupShuffleSplit(
        n_splits=1, test_size=0.4, random_state=SEED
    )
    _train_idx, rest_idx = next(gss1.split(X, y, groups=groups))
    rest_groups = [groups[i] for i in rest_idx]
    gss2 = GroupShuffleSplit(
        n_splits=1, test_size=0.5, random_state=SEED
    )
    _, test_local = next(
        gss2.split(X[rest_idx], y[rest_idx], groups=rest_groups)
    )
    return rest_idx[test_local]


def _predict(X, test_idx, trust_data):
    """Predict P(faithful) on test split using learned model."""
    params = trust_data["trust_model"]
    mean = np.array(params["mean"])
    scale = np.array(params["scale"])
    coef = np.array(params["coef"])
    intercept = params["intercept"]
    Z = (X[test_idx] - mean) / scale
    return 1.0 / (1.0 + np.exp(-(Z @ coef + intercept)))


# -------------------------------------------------------------------
# 1. Hallucination detection (RAGTruth test split)
# -------------------------------------------------------------------


def run_hallucination() -> dict:
    """Precision, recall, F1, AUROC on RAGTruth test split."""
    from sklearn.metrics import (
        classification_report,
        confusion_matrix,
        roc_auc_score,
    )

    trust_data = json.loads(TRUST_JSON.read_text(encoding="utf-8"))
    log.info("Hallucination eval on RAGTruth")

    X, y, groups = _process_ragtruth(trust_data)
    test_idx = _test_split(X, y, groups)
    probs = _predict(X, test_idx, trust_data)
    preds = (probs >= 0.5).astype(int)
    y_test = y[test_idx]

    auroc = float(roc_auc_score(y_test, probs))
    cm = confusion_matrix(y_test, preds).tolist()
    names = ["hallucinated", "faithful"]
    report = classification_report(
        y_test, preds, target_names=names, output_dict=True
    )

    result = {
        "test": "hallucination_detection",
        "n_test": len(test_idx),
        "auroc": round(auroc, 4),
        "precision_faithful": round(
            report["faithful"]["precision"], 4
        ),
        "recall_faithful": round(report["faithful"]["recall"], 4),
        "f1_faithful": round(report["faithful"]["f1-score"], 4),
        "precision_hallucinated": round(
            report["hallucinated"]["precision"], 4
        ),
        "recall_hallucinated": round(
            report["hallucinated"]["recall"], 4
        ),
        "f1_hallucinated": round(
            report["hallucinated"]["f1-score"], 4
        ),
        "confusion_matrix": cm,
        "accuracy": round(report["accuracy"], 4),
    }
    _save("hallucination", result)
    log.info(
        "Hallucination: AUROC=%.4f F1(faith)=%.4f F1(hall)=%.4f",
        auroc, result["f1_faithful"], result["f1_hallucinated"],
    )
    return result


# -------------------------------------------------------------------
# 2. Calibration: ECE, Brier, reliability diagram
# -------------------------------------------------------------------


def run_calibration() -> dict:
    """ECE, Brier score, reliability diagram from RAGTruth test split."""
    trust_data = json.loads(TRUST_JSON.read_text(encoding="utf-8"))
    metrics = trust_data.get("metrics", {})

    X, y, groups = _process_ragtruth(trust_data)
    test_idx = _test_split(X, y, groups)
    probs = _predict(X, test_idx, trust_data)
    y_test = y[test_idx]

    bins = np.linspace(0, 1, 11)
    diagram = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        mask = (probs >= lo) & (probs < hi)
        n = int(mask.sum())
        if n == 0:
            continue
        diagram.append({
            "predicted": round(float(probs[mask].mean()), 4),
            "observed": round(float(y_test[mask].mean()), 4),
            "n": n,
        })

    result = {
        "test": "calibration",
        "brier": metrics.get("brier"),
        "ece": metrics.get("ece"),
        "auroc": metrics.get("auroc"),
        "test_n": len(test_idx),
        "reliability_diagram": diagram,
    }
    _save("calibration", result)
    log.info(
        "Calibration: Brier=%.4f ECE=%.4f",
        result["brier"], result["ece"],
    )
    return result


# -------------------------------------------------------------------
# 3. Injected errors (NASA chunks)
# -------------------------------------------------------------------


def run_injected() -> dict:
    """Inject number/entity/negation errors into NASA claims.

    Report catch rate per type and false-alarm rate.
    """
    import random
    import re

    import pysbd

    from backend.calibration.trust_model import FALLBACK_NLI_THRESHOLDS
    from backend.db.client import chunks as get_chunks
    from backend.generation.llm import call_llm
    from backend.generation.schemas import Claim
    from backend.verification.gate import verify_claims

    temperature = json.loads(
        TRUST_JSON.read_text(encoding="utf-8")
    )["temperature"]
    thresholds = FALLBACK_NLI_THRESHOLDS
    rng = random.Random(SEED)

    nasa_chunks = list(get_chunks().find(
        {
            "file_name": {"$regex": "nasa", "$options": "i"},
            "element_type": "text",
        },
        {"embedding": 0},
    ).limit(300))
    log.info("Found %d NASA text chunks", len(nasa_chunks))
    if len(nasa_chunks) < 20:
        return {
            "test": "injected_errors",
            "skipped": True,
            "reason": "not enough NASA chunks",
        }

    good = [c for c in nasa_chunks if len(c.get("text", "")) >= 50]
    sample = rng.sample(good, min(100, len(good)))
    seg = pysbd.Segmenter(language="en", clean=False)

    def first_sentence(chunk: dict) -> str:
        sents = [
            s.strip()
            for s in seg.segment(chunk["text"])
            if len(s.strip()) > 20
        ]
        return sents[0] if sents else chunk["text"][:200]

    correct_claims = [
        {"text": first_sentence(c), "chunk": c} for c in sample
    ]

    def number_swap(text: str) -> str:
        match = re.search(r"\d+\.?\d*", text)
        if not match:
            return ""
        num = float(match.group())
        new = num * 2 + 7 if num != 0 else 42
        if "." not in match.group():
            new = int(new)
        return text[: match.start()] + str(new) + text[match.end() :]

    def entity_swap(text: str) -> str:
        words = text.split()
        caps = [
            (i, w)
            for i, w in enumerate(words)
            if w[0].isupper() and len(w) > 2 and i > 0
        ]
        if not caps:
            return ""
        idx, word = caps[0]
        pool = [
            "Mercury", "Jupiter", "Congress",
            "Boeing", "Russia", "Antarctica",
        ]
        pick = rng.choice(
            [r for r in pool if r != word] or pool
        )
        words[idx] = pick
        return " ".join(words)

    def negate(text: str) -> str:
        prompt = (
            "Negate this claim so it says the opposite. "
            "Return ONLY the negated claim.\n\n"
            f"Claim: {text}"
        )
        try:
            return call_llm(
                [{"role": "user", "content": prompt}],
                json_mode=False, reasoning_effort=None,
            )
        except (RuntimeError, ValueError) as e:
            log.warning("Negation LLM failed: %s", e)
            return ""

    def _verify_one(claim_text, evidence):
        claims_obj = [
            Claim(text=claim_text, cites=["[1]"], quote="")
        ]
        v = verify_claims(
            claims_obj, evidence, temperature, thresholds
        )
        return v[0]["label"]

    out = {
        "correct": [], "number_swap": [],
        "entity_swap": [], "negation": [],
    }

    for i, item in enumerate(correct_claims):
        chunk = item["chunk"]
        evidence = _make_evidence(chunk["text"], chunk["_id"])

        try:
            out["correct"].append(_verify_one(item["text"], evidence))
        except (ValueError, RuntimeError, KeyError):
            out["correct"].append("ERROR")

        ns = number_swap(item["text"])
        if ns:
            try:
                out["number_swap"].append(_verify_one(ns, evidence))
            except (ValueError, RuntimeError, KeyError):
                out["number_swap"].append("ERROR")

        es = entity_swap(item["text"])
        if es:
            try:
                out["entity_swap"].append(_verify_one(es, evidence))
            except (ValueError, RuntimeError, KeyError):
                out["entity_swap"].append("ERROR")

        if i < 30:
            neg = negate(item["text"])
            if neg:
                try:
                    out["negation"].append(
                        _verify_one(neg, evidence)
                    )
                except (ValueError, RuntimeError, KeyError):
                    out["negation"].append("ERROR")

        if (i + 1) % 25 == 0:
            log.info("  injected: %d / %d", i + 1, len(correct_claims))

    def rate(labels, target_not="SUPPORTED"):
        valid = [lb for lb in labels if lb != "ERROR"]
        if not valid:
            return 0.0
        return sum(lb != target_not for lb in valid) / len(valid)

    def label_counts(labels):
        valid = [lb for lb in labels if lb != "ERROR"]
        if not valid:
            return {}
        vals, counts = np.unique(valid, return_counts=True)
        return {str(v): int(c) for v, c in zip(vals, counts)}

    result = {
        "test": "injected_errors",
        "n_correct": len(out["correct"]),
        "n_number_swap": len(out["number_swap"]),
        "n_entity_swap": len(out["entity_swap"]),
        "n_negation": len(out["negation"]),
        "false_alarm_rate": round(rate(out["correct"]), 4),
        "catch_rate_number_swap": round(rate(out["number_swap"]), 4),
        "catch_rate_entity_swap": round(rate(out["entity_swap"]), 4),
        "catch_rate_negation": round(rate(out["negation"]), 4),
        "label_counts": {
            k: label_counts(v) for k, v in out.items()
        },
    }
    _save("injected_errors", result)
    log.info(
        "Injected: false_alarm=%.2f catch num=%.2f ent=%.2f neg=%.2f",
        result["false_alarm_rate"],
        result["catch_rate_number_swap"],
        result["catch_rate_entity_swap"],
        result["catch_rate_negation"],
    )
    return result


# -------------------------------------------------------------------
# 4. Retrieval: recall@5 and MRR
# -------------------------------------------------------------------


def run_retrieval() -> dict:
    """LLM-written questions with known gold chunk.

    Report recall@5 and MRR for vector, keyword, hybrid+rerank.
    """
    import random

    from backend.db.client import chunks as get_chunks
    from backend.generation.llm import call_llm
    from backend.models import rerank_scores
    from backend.retrieval.atlas_search import text_search, vector_search
    from backend.retrieval.fusion import rrf_fuse

    nasa_chunks = list(get_chunks().find(
        {
            "file_name": {"$regex": "nasa", "$options": "i"},
            "element_type": "text",
        },
        {"embedding": 0},
    ).limit(300))
    good = [c for c in nasa_chunks if len(c.get("text", "")) >= 100]
    if len(good) < 20:
        return {
            "test": "retrieval", "skipped": True,
            "reason": "not enough NASA chunks",
        }

    rng = random.Random(SEED)
    sample = rng.sample(good, min(100, len(good)))

    log.info("Generating %d questions from NASA chunks", len(sample))
    qa_pairs = []
    for i, chunk in enumerate(sample):
        prompt = (
            "Write ONE short factual question this passage answers. "
            "Return ONLY the question.\n\n"
            f"Passage: {chunk['text'][:500]}"
        )
        try:
            q = call_llm(
                [{"role": "user", "content": prompt}],
                json_mode=False, reasoning_effort=None,
            )
            qa_pairs.append({
                "question": q.strip(),
                "gold_id": chunk["_id"],
                "dataset_id": chunk["dataset_id"],
            })
        except (RuntimeError, ValueError) as e:
            log.warning("Question gen failed chunk %d: %s", i, e)
        if (i + 1) % 25 == 0:
            log.info("  questions: %d / %d", i + 1, len(sample))

    log.info("Generated %d QA pairs", len(qa_pairs))
    if not qa_pairs:
        return {
            "test": "retrieval", "skipped": True,
            "reason": "question generation failed",
        }

    def recall_mrr(hits, gold_id, k=5):
        ids = [r["_id"] for r in hits[:k]]
        if gold_id in ids:
            return 1, 1.0 / (ids.index(gold_id) + 1)
        return 0, 0.0

    vec_r, vec_m = [], []
    txt_r, txt_m = [], []
    hyb_r, hyb_m = [], []

    for i, qa in enumerate(qa_pairs):
        ds = qa["dataset_id"]
        try:
            hits = vector_search(qa["question"], ds, limit=10)
            r, m = recall_mrr(hits, qa["gold_id"])
            vec_r.append(r)
            vec_m.append(m)
        except (RuntimeError, ValueError, KeyError):
            pass

        try:
            hits = text_search(qa["question"], ds, limit=10)
            r, m = recall_mrr(hits, qa["gold_id"])
            txt_r.append(r)
            txt_m.append(m)
        except (RuntimeError, ValueError, KeyError):
            pass

        try:
            v = vector_search(qa["question"], ds, limit=30)
            t = text_search(qa["question"], ds, limit=30)
            fused = rrf_fuse(v, t)
            passages = [x.get("text", "") for x in fused[:10]]
            scores = rerank_scores(qa["question"], passages)
            for j, s in enumerate(scores):
                fused[j]["_rerank_score"] = s
            reranked = sorted(
                fused[:10],
                key=lambda x: x.get("_rerank_score", 0),
                reverse=True,
            )
            r, m = recall_mrr(reranked, qa["gold_id"])
            hyb_r.append(r)
            hyb_m.append(m)
        except (RuntimeError, ValueError, KeyError):
            pass

        if (i + 1) % 25 == 0:
            log.info("  retrieval: %d / %d", i + 1, len(qa_pairs))

    def _avg(arr):
        return round(float(np.mean(arr)), 4) if arr else None

    result = {
        "test": "retrieval",
        "n_queries": len(qa_pairs),
        "vector": {
            "recall_at_5": _avg(vec_r),
            "mrr": _avg(vec_m), "n": len(vec_r),
        },
        "keyword": {
            "recall_at_5": _avg(txt_r),
            "mrr": _avg(txt_m), "n": len(txt_r),
        },
        "hybrid_rerank": {
            "recall_at_5": _avg(hyb_r),
            "mrr": _avg(hyb_m), "n": len(hyb_r),
        },
    }
    _save("retrieval", result)
    log.info(
        "Retrieval: vec R@5=%s MRR=%s, kw R@5=%s MRR=%s, hyb R@5=%s MRR=%s",
        result["vector"]["recall_at_5"], result["vector"]["mrr"],
        result["keyword"]["recall_at_5"], result["keyword"]["mrr"],
        result["hybrid_rerank"]["recall_at_5"],
        result["hybrid_rerank"]["mrr"],
    )
    return result


# -------------------------------------------------------------------
# 5. End-to-end: gate vs no gate
# -------------------------------------------------------------------


def run_e2e() -> dict:
    """Coverage with gate, decisions, bootstrap 95% CIs."""
    import random
    from collections import Counter

    from scipy.stats import bootstrap as sp_bootstrap

    from backend.calibration.trust_model import (
        decide_trust,
        get_nli_thresholds,
        get_temperature,
        predict_trust,
    )
    from backend.db.client import chunks as get_chunks
    from backend.generation.answer import generate_answer
    from backend.generation.llm import call_llm
    from backend.generation.prompts import format_context
    from backend.retrieval.atlas_search import (
        text_search,
        vector_search,
    )
    from backend.retrieval.context import build_context
    from backend.retrieval.fusion import rrf_fuse
    from backend.retrieval.reranker import rerank
    from backend.verification.features import extract_features
    from backend.verification.gate import run_gate

    rng = random.Random(SEED)

    nasa_chunks = list(get_chunks().find(
        {
            "file_name": {"$regex": "nasa", "$options": "i"},
            "element_type": "text",
        },
        {"embedding": 0},
    ).limit(200))
    good = [c for c in nasa_chunks if len(c.get("text", "")) >= 100]
    if len(good) < 20:
        return {
            "test": "e2e", "skipped": True,
            "reason": "not enough chunks",
        }

    sample = rng.sample(good, min(50, len(good)))
    dataset_id = sample[0]["dataset_id"]

    questions = []
    for chunk in sample:
        prompt = (
            "Write ONE short factual question about this passage. "
            "Return ONLY the question.\n\n"
            f"{chunk['text'][:400]}"
        )
        try:
            q = call_llm(
                [{"role": "user", "content": prompt}],
                json_mode=False, reasoning_effort=None,
            )
            questions.append(q.strip())
        except (RuntimeError, ValueError):
            continue

    log.info("E2E: %d questions through full pipeline", len(questions))
    temperature = get_temperature()
    thresholds = get_nli_thresholds()

    gate_shown = []
    decisions = []

    for i, q in enumerate(questions):
        try:
            fused = rrf_fuse(
                vector_search(q, dataset_id),
                text_search(q, dataset_id),
            )
            evidence = build_context(rerank(q, fused))
            context = format_context(evidence)
            first = generate_answer(q, context)
            gate = run_gate(
                q, context, evidence, first,
                temperature, thresholds,
            )
            features = extract_features(
                gate["claims"], evidence, gate["repaired"]
            )
            trust = predict_trust(features)
            decision = decide_trust(trust)
            decisions.append(decision)
            blocked = (
                decision == "Withheld"
                or gate["decision"] == "BLOCK"
            )
            gate_shown.append(0 if blocked else 1)
        except (RuntimeError, ValueError, KeyError) as e:
            log.warning("E2E question %d failed: %s", i, e)
        if (i + 1) % 10 == 0:
            log.info("  e2e: %d / %d", i + 1, len(questions))

    if not gate_shown:
        return {
            "test": "e2e", "skipped": True,
            "reason": "all questions failed",
        }

    gate_arr = np.array(gate_shown)
    coverage = float(gate_arr.mean())
    ci = sp_bootstrap(
        (gate_arr,), np.mean,
        confidence_level=0.95, random_state=SEED,
        method="percentile",
    )
    decision_counts = dict(Counter(decisions))

    result = {
        "test": "e2e",
        "n_questions": len(questions),
        "n_answered": len(gate_shown),
        "coverage": round(coverage, 4),
        "coverage_ci_95": [
            round(ci.confidence_interval.low, 4),
            round(ci.confidence_interval.high, 4),
        ],
        "decisions": decision_counts,
        "without_gate_shown": len(gate_shown),
    }
    _save("e2e", result)
    log.info(
        "E2E: coverage=%.2f [%.2f, %.2f] decisions=%s",
        coverage, result["coverage_ci_95"][0],
        result["coverage_ci_95"][1], decision_counts,
    )
    return result


# -------------------------------------------------------------------
# Report
# -------------------------------------------------------------------


def write_report(results: dict) -> None:
    """Write results/REPORT.md summary."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Argus Evaluation Report",
        f"Date: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    if "hallucination" in results:
        r = results["hallucination"]
        lines += [
            "## 1. Hallucination Detection (RAGTruth test split)",
            f"- AUROC: {r.get('auroc')}",
            f"- Precision (faithful): {r.get('precision_faithful')}",
            f"- Recall (faithful): {r.get('recall_faithful')}",
            f"- F1 (faithful): {r.get('f1_faithful')}",
            f"- F1 (hallucinated): {r.get('f1_hallucinated')}",
            f"- Accuracy: {r.get('accuracy')}",
            f"- Confusion matrix: {r.get('confusion_matrix')}",
            "",
        ]

    if "calibration" in results:
        r = results["calibration"]
        lines += [
            "## 2. Calibration",
            f"- Brier score: {r.get('brier')}",
            f"- ECE: {r.get('ece')}",
            f"- AUROC: {r.get('auroc')}",
            f"- Reliability diagram: "
            f"{len(r.get('reliability_diagram', []))} bins",
            "",
        ]

    if "injected" in results:
        r = results["injected"]
        if r.get("skipped"):
            lines += [
                "## 3. Injected Errors",
                f"- Skipped: {r.get('reason')}",
                "",
            ]
        else:
            lines += [
                "## 3. Injected Errors (NASA chunks)",
                f"- Correct claims: {r.get('n_correct')}",
                f"- False alarm rate: {r.get('false_alarm_rate')}",
                f"- Catch (number swap): "
                f"{r.get('catch_rate_number_swap')}",
                f"- Catch (entity swap): "
                f"{r.get('catch_rate_entity_swap')}",
                f"- Catch (negation): "
                f"{r.get('catch_rate_negation')}",
                "",
            ]

    if "retrieval" in results:
        r = results["retrieval"]
        if r.get("skipped"):
            lines += [
                "## 4. Retrieval",
                f"- Skipped: {r.get('reason')}",
                "",
            ]
        else:
            v = r["vector"]
            k = r["keyword"]
            h = r["hybrid_rerank"]
            lines += [
                "## 4. Retrieval (NASA chunks)",
                f"- Queries: {r.get('n_queries')}",
                f"- Vector: R@5={v.get('recall_at_5')} "
                f"MRR={v.get('mrr')}",
                f"- Keyword: R@5={k.get('recall_at_5')} "
                f"MRR={k.get('mrr')}",
                f"- Hybrid+rerank: R@5={h.get('recall_at_5')} "
                f"MRR={h.get('mrr')}",
                "",
            ]

    if "e2e" in results:
        r = results["e2e"]
        if r.get("skipped"):
            lines += [
                "## 5. End-to-End",
                f"- Skipped: {r.get('reason')}",
                "",
            ]
        else:
            lines += [
                "## 5. End-to-End",
                f"- Questions: {r.get('n_questions')}, "
                f"answered: {r.get('n_answered')}",
                f"- Coverage: {r.get('coverage')} "
                f"{r.get('coverage_ci_95')}",
                f"- Decisions: {r.get('decisions')}",
                "",
            ]

    report = "\n".join(lines)
    path = RESULTS_DIR / "REPORT.md"
    path.write_text(report, encoding="utf-8")
    log.info("Wrote %s", path)


# -------------------------------------------------------------------
# CLI
# -------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Argus evaluation runner"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all tests"
    )
    parser.add_argument("--hallucination", action="store_true")
    parser.add_argument("--calibration", action="store_true")
    parser.add_argument("--injected", action="store_true")
    parser.add_argument("--retrieval", action="store_true")
    parser.add_argument("--e2e", action="store_true")
    args = parser.parse_args()

    flags = [
        args.all, args.hallucination, args.calibration,
        args.injected, args.retrieval, args.e2e,
    ]
    if not any(flags):
        parser.print_help()
        sys.exit(1)

    results = {}
    tests = [
        (args.all or args.hallucination, "hallucination",
         run_hallucination),
        (args.all or args.calibration, "calibration",
         run_calibration),
        (args.all or args.injected, "injected",
         run_injected),
        (args.all or args.retrieval, "retrieval",
         run_retrieval),
        (args.all or args.e2e, "e2e", run_e2e),
    ]
    for enabled, name, fn in tests:
        if enabled:
            try:
                results[name] = fn()
            except (RuntimeError, ValueError, OSError) as e:
                log.error("%s test failed: %s", name, e)

    if results:
        write_report(results)

    print("\n=== Evaluation complete ===")


if __name__ == "__main__":
    main()
