"""run_question(): one question end to end. Used by the API, the CLI, eval and calibration."""

import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone

from backend.calibration.trust_model import (
    get_nli_thresholds,
    get_temperature,
    predict_trust,
)
from backend.common.ids import make_id
from backend.db.client import queries
from backend.generation.answer import generate_answer
from backend.generation.prompts import format_context
from backend.retrieval.atlas_search import text_search, vector_search
from backend.retrieval.context import build_context, citable
from backend.retrieval.fusion import rrf_fuse
from backend.retrieval.reranker import rerank
from backend.verification.aggregate import count_labels
from backend.verification.chart_data import chart_from_chunk
from backend.verification.features import extract_features
from backend.verification.gate import run_gate

log = logging.getLogger(__name__)

EVIDENCE_PREVIEW_CHARS = 600
StageFn = Callable[[dict], None]


def run_question(
    question: str,
    dataset_id: str,
    document_ids: list[str] | None = None,
    session: dict | None = None,
    on_stage: StageFn | None = None,
) -> dict:
    """Retrieve -> generate -> verify -> store. Returns the result."""
    stage = on_stage or (lambda _event: None)
    timer = _Timer()

    stage({"stage": "searching"})
    fused = rrf_fuse(
        vector_search(question, dataset_id, document_ids),
        text_search(question, dataset_id, document_ids),
    )
    timer.lap("retrieve")
    evidence = build_context(rerank(question, fused))
    timer.lap("rerank")

    stage({"stage": "reading", "passages": len(citable(evidence))})
    context = format_context(evidence)
    stage({"stage": "drafting"})
    first = generate_answer(question, context)
    timer.lap("llm")

    temperature = get_temperature()
    thresholds = get_nli_thresholds()

    gate = run_gate(
        question,
        context,
        evidence,
        first,
        temperature,
        thresholds,
        on_stage=stage,
    )
    timer.lap("verify")

    features = extract_features(gate["claims"], evidence, gate["repaired"])
    trust = predict_trust(features)
    result = _result(question, dataset_id, session, evidence, gate, trust, features, timer.done())
    _store(result, dataset_id, document_ids, gate, features)
    stage({"stage": "done"})
    return result


def _result(question, dataset_id, session, evidence, gate, trust, features, latency) -> dict:
    claims = gate["claims"]
    shown = citable(evidence)
    return {
        "query_id": make_id("q_"),
        "session_id": session["_id"] if session else None,
        "turn": session["turns"] + 1 if session else 1,
        "question": question,
        "decision": gate["decision"],
        "trust": trust,
        "answer": gate["answer"],
        "claims": claims,
        "evidence": [_evidence_card(c) for c in shown],
        "score_card": {
            "claims": count_labels(claims),
            "evidence_types": sorted({c.get("element_type", "text") for c in shown}),
            "min_support": features.get("min_support", 0.0),
            "numbers_ok": all(c["checks"]["numbers_ok"] for c in claims),
            "quotes_ok": all(c["checks"]["quote_match"] for c in claims),
            "top_retrieval": features.get("top1_rerank", 0.0),
            "repaired": gate["repaired"],
        },
        "blocked_reason": gate["blocked_reason"],
        "latency_ms": latency,
    }


def _evidence_card(c: dict) -> dict:
    card = {
        "ref": c["_ref"],
        "chunk_id": c["_id"],
        "document_id": c.get("document_id"),
        "file_name": c.get("file_name"),
        "page": c.get("page"),
        "type": c.get("element_type"),
        "section": " › ".join(c.get("heading_path", [])),
        "text": c.get("text", "")[:EVIDENCE_PREVIEW_CHARS],
        "bbox": c.get("bbox"),
        "rerank": round(c.get("_rerank_score", 0.0), 4),
    }
    chart = chart_from_chunk(c)
    if chart:
        card["chart"] = chart
    return card


def _store(result: dict, dataset_id: str, document_ids, gate: dict, features: dict) -> None:
    """Store query result for audit trail."""
    queries().insert_one(
        {
            **result,
            "_id": result["query_id"],
            "dataset_id": dataset_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": "cross" if document_ids and len(document_ids) > 1 else "single",
            "document_ids": document_ids or [],
            "attempts": gate["attempts"],
            "features": features,
            "feedback": {"value": None, "reason": None},
        }
    )


class _Timer:
    """Milliseconds per stage plus total."""

    def __init__(self) -> None:
        self.start = self.last = time.perf_counter()
        self.laps: dict[str, int] = {}

    def lap(self, name: str) -> None:
        now = time.perf_counter()
        self.laps[name] = int((now - self.last) * 1000)
        self.last = now

    def done(self) -> dict:
        return {**self.laps, "total": int((time.perf_counter() - self.start) * 1000)}
