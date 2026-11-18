"""Verification gate: check every claim against its evidence and decide the answer."""

from rapidfuzz import fuzz

from backend.common.text import evidence_text, sentence_spans
from backend.config import settings
from backend.generation.schemas import AnswerOutput, Claim
from backend.retrieval.context import citable
from backend.verification.aggregate import CONTRADICTED, UNVERIFIED, decide_answer, label_claim
from backend.verification.checks import find_quote, number_problems, quotations_ok
from backend.verification.nli import nli_scores

MAX_CHUNKS_PER_CLAIM = 4
EXTRA_CHUNKS = 3
BLOCK_EVIDENCE_CHARS = 400
NO_SCORES = {"ent": 0.0, "neu": 1.0, "con": 0.0}


def run_gate(draft: AnswerOutput, evidence: list[dict], temperature: float, thresholds: dict, on_stage=None) -> dict:
    """Verify a draft and decide: ACCEPT, ACCEPT_LOW_CONFIDENCE, WARN, BLOCK or NO_SUPPORT."""
    if on_stage:
        on_stage({"stage": "checking", "claims": len(draft.claims)})
    claims = [] if draft.not_found else verify_claims(draft.claims, evidence, temperature, thresholds)
    decision = decide_answer([c["label"] for c in claims], draft.not_found)
    return {
        "decision": decision,
        "answer": "" if decision in ("BLOCK", "NO_SUPPORT") else draft.answer,
        "claims": claims,
        "model": draft.model,
        "blocked_reason": _blocked_reason(claims, evidence) if decision == "BLOCK" else None,
    }


def verify_claims(claims: list[Claim], evidence: list[dict], temperature: float, thresholds: dict) -> list[dict]:
    """NLI for every claim in one batch, plus quote and number checks and a label per claim.

    Premises are the candidate chunks plus the few 1-2 sentence windows that best match the claim:
    NLI models judge a short, precise premise much better than a long passage.
    """
    ranked = citable(evidence)
    by_ref = {c["_ref"]: c for c in ranked}
    plans = []
    for claim in claims:
        chunks = _chunks_for(claim, ranked, by_ref)
        plans.append((chunks, _windows(claim.text, chunks)))
    pairs = [
        (text, claim.text)
        for claim, (chunks, windows) in zip(claims, plans)
        for text in [evidence_text(c) for c in chunks] + [w["text"] for w in windows]
    ]
    scores = iter(nli_scores(pairs, temperature))
    out = []
    for claim, (chunks, windows) in zip(claims, plans):
        chunk_scores = [next(scores) for _ in chunks]
        window_scores = [next(scores) for _ in windows]
        out.append(_verify_one(claim, chunks, chunk_scores, windows, window_scores, thresholds))
    return out


def _chunks_for(claim: Claim, ranked: list[dict], by_ref: dict) -> list[dict]:
    """Cited chunks plus the best-reranked others, at most MAX_CHUNKS_PER_CLAIM."""
    cited = [by_ref[r] for r in claim.cites if r in by_ref]
    others = [c for c in ranked if c not in cited][:EXTRA_CHUNKS]
    return (cited + others)[:MAX_CHUNKS_PER_CLAIM]


def _windows(claim: str, chunks: list[dict]) -> list[dict]:
    """The 1-2 sentence windows (across the candidate chunks) lexically closest to the claim."""
    found = []
    for i, chunk in enumerate(chunks):
        text = evidence_text(chunk)
        spans = sentence_spans(text)
        if len(spans) < 2:
            continue  # the chunk itself is already a single sentence
        for j, (start, _) in enumerate(spans):
            for end in {spans[j][1], spans[min(j + 1, len(spans) - 1)][1]}:
                window = text[start:end].strip()
                found.append({"chunk": i, "text": window, "span": [start, end],
                              "match": fuzz.token_set_ratio(claim, window)})
    found.sort(key=lambda w: w["match"], reverse=True)
    return found[: settings.NLI_WINDOWS_PER_CLAIM]


def _verify_one(claim, chunks, chunk_scores, windows, window_scores, thresholds) -> dict:
    if not chunks:
        return _result(claim, UNVERIFIED, NO_SCORES, 0.0, [], _empty_checks(), {})
    premises = [(i, s, None) for i, s in enumerate(chunk_scores)]
    premises += [(w["chunk"], s, w["span"]) for w, s in zip(windows, window_scores)]
    best_chunk, best_scores, best_span = max(premises, key=lambda p: p[1]["ent"])
    best = chunks[best_chunk]

    # Contradiction only from whole cited chunks (or the best chunk if nothing is cited):
    # an unrelated passage, or a single sentence out of context, must not block an answer.
    cited = [i for i, c in enumerate(chunks) if c["_ref"] in claim.cites] or [best_chunk]
    contra = max(chunk_scores[i]["con"] for i in cited)
    checked = [chunks[i] for i in sorted(set(cited) | {best_chunk})]
    check_text = "\n".join(evidence_text(c) for c in checked)
    all_text = "\n".join(evidence_text(c) for c in chunks)

    quote = claim.quote or claim.text
    quote_found, quote_score, _ = find_quote(quote, check_text)
    if not quote_found:
        quote_found, quote_score, _ = find_quote(quote, all_text)  # citation slightly off
    number_detail = number_problems(claim.text, check_text)
    quote_source = "model" if quote_found else None
    if not quote_found and best_span and best_scores["ent"] >= thresholds["tau_accept"] and not number_detail:
        # The model gave no usable quote, but one source sentence entails the claim on its own:
        # that sentence is the anchor (shown highlighted), which is at least as strict as a quote.
        quote = evidence_text(best)[best_span[0] : best_span[1]]
        quote_found, quote_score, quote_source = True, 1.0, "verifier"
    checks = {
        "quote_match": quote_found,
        "quote_source": quote_source,
        "quote_score": round(quote_score, 3),
        "quotations_ok": quotations_ok(claim.text, check_text),
        "numbers_ok": not number_detail,
        "number_detail": number_detail,
    }
    label = label_claim(
        best_scores["ent"], contra, quote_found, checks["quotations_ok"], checks["numbers_ok"], thresholds
    )
    _, _, quote_span = find_quote(quote, evidence_text(best))
    highlight = {"chunk_id": best["_id"], "ref": best["_ref"], "page": best.get("page"),
                 "span": quote_span or best_span}
    nli = [{"ref": c["_ref"], **{k: round(v, 4) for k, v in s.items()}} for c, s in zip(chunks, chunk_scores)]
    if not any(c["_ref"] in claim.cites for c in chunks):
        # Uncited claim (or a ref that isn't in the context): cite the passage that supports it best.
        claim = claim.model_copy(update={"cites": [best["_ref"]]})
    if quote_source == "verifier":
        claim = claim.model_copy(update={"quote": quote})
    return _result(claim, label, best_scores, contra, nli, checks, highlight)


def _result(claim, label, scores, contra, nli, checks, highlight) -> dict:
    """One verified claim. `scores` is the full NLI split from the best-supporting premise."""
    return {
        "text": claim.text,
        "cites": claim.cites,
        "quote": claim.quote,
        "label": label,
        "scores": {
            "entailment": round(scores["ent"], 4),
            "neutral": round(scores["neu"], 4),
            "contradiction": round(scores["con"], 4),
        },
        "support": round(scores["ent"], 4),
        "contra": round(contra, 4),
        "nli": nli,
        "checks": checks,
        "highlight": highlight,
    }


def _empty_checks() -> dict:
    return {"quote_match": False, "quote_source": None, "quote_score": 0.0, "quotations_ok": True,
            "numbers_ok": True, "number_detail": ""}


def _blocked_reason(claims: list[dict], evidence: list[dict]) -> dict | None:
    """'The draft said X. Page N says Y.' for the first contradicted claim."""
    by_ref = {c["_ref"]: c for c in evidence}
    claim = next((c for c in claims if c["label"] == CONTRADICTED), None)
    if claim is None:
        return None
    if not claim["checks"]["quotations_ok"]:
        reason, ref = "the quotation does not match the source", claim["highlight"].get("ref")
    else:
        cited = [s for s in claim["nli"] if s["ref"] in claim["cites"]] or claim["nli"]
        ref = max(cited, key=lambda s: s["con"])["ref"] if cited else claim["highlight"].get("ref")
        reason = "the source contradicts it"
    chunk = by_ref.get(ref, {})
    return {
        "draft_claim": claim["text"],
        "reason": reason,
        "evidence_ref": ref,
        "page": chunk.get("page"),
        "evidence_text": evidence_text(chunk)[:BLOCK_EVIDENCE_CHARS],
    }
