"""Verification gate: check every claim and decide. No repair loop."""

import logging

from backend.common.text import evidence_text
from backend.generation.schemas import AnswerOutput, Claim
from backend.retrieval.context import citable
from backend.verification.aggregate import CONTRADICTED, UNVERIFIED, decide_answer, label_claim
from backend.verification.checks import find_quote, number_problems, quotations_ok
from backend.verification.nli import nli_scores

log = logging.getLogger(__name__)

MAX_CHUNKS_PER_CLAIM = 4
EXTRA_CHUNKS = 3


def run_gate(
    question: str,
    context: str,
    evidence: list[dict],
    first: AnswerOutput,
    temperature: float,
    thresholds: dict,
    on_stage=None,
    **_kwargs,
) -> dict:
    """Verify a draft. No repair — single attempt only."""
    stage = on_stage or (lambda _event: None)
    stage({"stage": "checking", "claims": len(first.claims)})
    attempt = _attempt(1, first, evidence, temperature, thresholds)
    return {
        "decision": attempt["decision"],
        "answer": "" if attempt["decision"] in ("BLOCK", "NO_SUPPORT") else attempt["answer"],
        "claims": attempt["claims"],
        "repaired": False,
        "attempts": [attempt],
        "blocked_reason": (
            _blocked_reason(attempt["claims"], evidence, thresholds["tau_rel"])
            if attempt["decision"] == "BLOCK"
            else None
        ),
    }


def verify_claims(
    claims: list[Claim], evidence: list[dict], temperature: float, thresholds: dict
) -> list[dict]:
    """NLI (one batch for all claims) plus quote/number checks and a label for each claim."""
    ranked = citable(evidence)
    by_ref = {c["_ref"]: c for c in ranked}
    plans = [_chunks_for(claim, ranked, by_ref) for claim in claims]
    pairs = [(evidence_text(ch), claim.text) for claim, chs in zip(claims, plans) for ch in chs]
    scores = iter(nli_scores(pairs, temperature))
    return [
        _verify_one(claim, chs, [next(scores) for _ in chs], thresholds) for claim, chs in zip(claims, plans)
    ]


def _chunks_for(claim: Claim, ranked: list[dict], by_ref: dict) -> list[dict]:
    """Cited chunks plus the best-reranked others, at most MAX_CHUNKS_PER_CLAIM."""
    cited = [by_ref[r] for r in claim.cites if r in by_ref]
    others = [c for c in ranked if c not in cited][:EXTRA_CHUNKS]
    return (cited + others)[:MAX_CHUNKS_PER_CLAIM]


def _verify_one(claim: Claim, chunks: list[dict], scores: list[dict], thresholds: dict) -> dict:
    if not chunks:
        return _result(claim, UNVERIFIED, 0.0, 0.0, [], {}, None)
    support = max(s["ent"] for s in scores)

    # Contradiction only from cited chunks (fall back to best-entailing chunk)
    cited_indices = [i for i, c in enumerate(chunks) if c["_ref"] in claim.cites]
    if not cited_indices:
        cited_indices = [max(range(len(chunks)), key=lambda i: scores[i]["ent"])]
    contra = max(scores[i]["con"] for i in cited_indices)

    best = chunks[max(range(len(chunks)), key=lambda i: scores[i]["ent"])]

    cited = [chunks[i] for i in cited_indices]
    check_text = "\n".join(evidence_text(c) for c in cited)
    quote_found, quote_score, _ = find_quote(claim.quote, check_text)
    number_detail = number_problems(claim.text, check_text)
    checks = {
        "quote_match": quote_found,
        "quote_score": round(quote_score, 3),
        "quotations_ok": quotations_ok(claim.text, check_text),
        "numbers_ok": not number_detail,
        "number_detail": number_detail,
    }
    label = label_claim(
        support, contra, quote_found, checks["quotations_ok"], checks["numbers_ok"], thresholds
    )
    nli = [{"ref": c["_ref"], **{k: round(v, 4) for k, v in s.items()}} for c, s in zip(chunks, scores)]
    return _result(claim, label, support, contra, nli, checks, best)


def _result(claim, label, support, contra, nli, checks, best) -> dict:
    highlight = {}
    if best is not None:
        _, _, span = find_quote(claim.quote, best.get("text", ""))
        highlight = {"chunk_id": best["_id"], "ref": best["_ref"], "page": best.get("page"), "span": span}
    return {
        "text": claim.text,
        "cites": claim.cites,
        "quote": claim.quote,
        "label": label,
        "support": round(support, 4),
        "contra": round(contra, 4),
        "nli": nli,
        "checks": checks
        or {
            "quote_match": False,
            "quote_score": 0.0,
            "quotations_ok": True,
            "numbers_ok": True,
            "number_detail": "",
        },
        "highlight": highlight,
    }


def _attempt(n: int, draft: AnswerOutput, evidence, temperature, thresholds) -> dict:
    claims = [] if draft.not_found else verify_claims(draft.claims, evidence, temperature, thresholds)
    return {
        "n": n,
        "model": draft.model,
        "not_found": draft.not_found,
        "answer": draft.answer,
        "decision": decide_answer([c["label"] for c in claims], draft.not_found),
        "claims": claims,
    }


def _blocked_reason(claims: list[dict], evidence: list[dict], tau_rel: float) -> dict | None:
    """'The draft said X. Page N says Y.' for the first contradicted claim."""
    by_ref = {c["_ref"]: c for c in evidence}
    claim = next((c for c in claims if c["label"] == CONTRADICTED), None)
    if claim is None:
        return None
    if not claim["checks"]["quotations_ok"]:
        reason, ref = "the quotation does not match the source", claim["highlight"].get("ref")
    else:
        relevant = [s for s in claim["nli"] if by_ref.get(s["ref"], {}).get("_rerank_score", 0.0) >= tau_rel]
        ref = max(relevant, key=lambda s: s["con"])["ref"] if relevant else claim["highlight"].get("ref")
        reason = "the source contradicts it"
    chunk = by_ref.get(ref, {})
    return {
        "draft_claim": claim["text"],
        "reason": reason,
        "evidence_ref": ref,
        "page": chunk.get("page"),
        "evidence_text": evidence_text(chunk)[:400],
    }
