"""run_question(): one question end to end. Used by the API, the CLI, the eval and smoke tests."""

import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone

from backend.calibration.trust_model import calibration_info, get_nli_thresholds, get_temperature, predict_trust
from backend.common.ids import make_id
from backend.config import settings
from backend.db.client import queries
from backend.generation.answer import generate_answer
from backend.generation.prompts import format_context
from backend.retrieval.atlas_search import text_search, vector_search
from backend.retrieval.context import build_context, citable
from backend.retrieval.fusion import rrf_fuse
from backend.retrieval.reranker import rerank
from backend.sessions import record_turn
from backend.verification.aggregate import count_labels
from backend.verification.chart_data import chart_from_chunk
from backend.verification.features import extract_features, nli_means
from backend.verification.gate import run_gate

log = logging.getLogger(__name__)

EVIDENCE_PREVIEW_CHARS = 600
StageFn = Callable[[dict], None]


def retrieve(question: str, dataset_id: str, document_ids: list[str] | None = None) -> list[dict]:
    """Vector + keyword search, RRF fusion, rerank, then the context with C/N refs."""
    fused = rrf_fuse(
        vector_search(question, dataset_id, document_ids),
        text_search(question, dataset_id, document_ids),
    )
    return build_context(rerank(question, fused))


def answer_and_verify(question: str, evidence: list[dict], on_stage: StageFn | None = None, timer=None) -> dict:
    """Draft (with one retry on a doubtful 'not found'), verify, score. No database writes."""
    stage = on_stage or (lambda _event: None)
    lap = timer.lap if timer else (lambda _name: None)
    shown = citable(evidence)
    context = format_context(evidence)
    stage({"stage": "drafting"})
    draft = generate_answer(question, context)
    top = shown[0].get("_rerank_score", 0.0) if shown else 0.0
    if draft.not_found and top >= settings.NOT_FOUND_RETRY_MIN_RERANK:
        log.info("Draft said not found but top passage scored %.2f; asking once more", top)
        stage({"stage": "drafting", "retry": True})
        draft = generate_answer(question, context, retry_not_found=True)
    lap("llm")
    gate = run_gate(draft, evidence, get_temperature(), get_nli_thresholds(), on_stage=stage)
    lap("verify")
    features = extract_features(gate["claims"], evidence)
    return {**gate, "features": features, "trust": predict_trust(features)}


def run_question(
    question: str,
    dataset_id: str,
    document_ids: list[str] | None = None,
    session: dict | None = None,
    on_stage: StageFn | None = None,
) -> dict:
    """Retrieve -> generate -> verify -> store. Returns the result (spec 12.1)."""
    stage = on_stage or (lambda _event: None)
    timer = _Timer()
    stage({"stage": "searching"})
    evidence = retrieve(question, dataset_id, document_ids)
    timer.lap("retrieve")
    stage({"stage": "reading", "passages": len(citable(evidence))})
    checked = answer_and_verify(question, evidence, stage, timer)
    result = _result(question, session, evidence, checked, timer.done())
    _store(result, dataset_id, document_ids, checked)
    stage({"stage": "done"})
    return result


def _result(question: str, session: dict | None, evidence: list[dict], checked: dict, latency: dict) -> dict:
    claims = checked["claims"]
    shown = citable(evidence)
    features = checked["features"]
    calibration = calibration_info()
    return {
        "query_id": make_id("q_"),
        "session_id": session["_id"] if session else None,
        "turn": session["turns"] + 1 if session else 1,
        "question": question,
        "decision": checked["decision"],
        "trust": checked["trust"],
        "answer": checked["answer"],
        "claims": claims,
        "evidence": [_evidence_card(c) for c in shown],
        "score_card": {
            "claims": count_labels(claims),
            "nli": nli_means(claims),
            "evidence_types": sorted({c.get("element_type", "text") for c in shown}),
            "min_support": features.get("min_support", 0.0),
            "numbers_ok": all(c["checks"]["numbers_ok"] for c in claims),
            "quotes_ok": all(c["checks"]["quote_match"] for c in claims),
            "top_retrieval": features.get("top1_rerank", shown[0].get("_rerank_score", 0.0) if shown else 0.0),
            "calibration": {
                "version": calibration.get("version"),
                "thresholds": calibration["thresholds"],
                "fallback": calibration["fallback"],
            },
        },
        "model": checked["model"],
        "blocked_reason": checked["blocked_reason"],
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


def _store(result: dict, dataset_id: str, document_ids: list[str] | None, checked: dict) -> None:
    """Store the full trace, then update the conversation's running totals."""
    queries().insert_one(
        {
            **result,
            "_id": result["query_id"],
            "dataset_id": dataset_id,
            "ts": datetime.now(timezone.utc).isoformat(),
            "mode": "cross" if document_ids and len(document_ids) > 1 else "single",
            "document_ids": document_ids or [],
            "features": checked["features"],
            "feedback": {"value": None, "reason": None},
        }
    )
    if result["session_id"]:
        result["session_summary"] = record_turn(
            result["session_id"], result["question"], result["decision"], result["trust"]
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
