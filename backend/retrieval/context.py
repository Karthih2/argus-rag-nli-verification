"""Build the answer context: drop near-duplicates, add neighbours of lone hits, cap tokens."""

from backend.common.text import approx_tokens, evidence_text
from backend.config import settings
from backend.db.client import chunks

DUPLICATE_OVERLAP = 0.5
TABLE_TYPES = {"table", "table_full"}


def build_context(reranked: list[dict], max_tokens: int | None = None) -> list[dict]:
    """Evidence for the prompt, in reading order.

    Hits get citable refs C1, C2, ...; neighbours get N1, N2, ... (visible, never citable).
    """
    hits = _dedupe(reranked)  # best reranked first
    budget = max_tokens or settings.CONTEXT_MAX_TOKENS
    kept, used = [], 0
    # Fill the budget by priority (hits by rerank, then neighbours), then show in reading order.
    for chunk in hits + _neighbours_of_lone_hits(hits):
        cost = approx_tokens(evidence_text(chunk))
        if kept and used + cost > budget:
            continue  # skip this one; a shorter later chunk may still fit
        kept.append(chunk)
        used += cost
    kept.sort(key=lambda c: (c.get("document_id", ""), c.get("seq", 0)))

    n_hit = n_nb = 0
    for chunk in kept:
        if chunk.get("_is_neighbour"):
            n_nb += 1
            chunk["_ref"] = f"N{n_nb}"
        else:
            n_hit += 1
            chunk["_ref"] = f"C{n_hit}"
    return kept


def citable(evidence: list[dict]) -> list[dict]:
    """Evidence chunks the model may cite (no neighbours), best reranked first."""
    hits = [c for c in evidence if not c.get("_is_neighbour")]
    return sorted(hits, key=lambda c: c.get("_rerank_score", 0.0), reverse=True)


def _dedupe(ranked: list[dict]) -> list[dict]:
    kept: list[dict] = []
    for chunk in ranked:
        if not any(
            _same_place(chunk, k) and _overlap(chunk, k) > DUPLICATE_OVERLAP for k in kept
        ):
            kept.append(chunk)
    return kept


def _neighbours_of_lone_hits(hits: list[dict]) -> list[dict]:
    """seq ± 1 for a text hit that is the only hit from its section."""

    def section(c: dict) -> tuple:
        return c.get("document_id"), tuple(c.get("heading_path", []))

    counts: dict[tuple, int] = {}
    for c in hits:
        counts[section(c)] = counts.get(section(c), 0) + 1
    have = {c["_id"] for c in hits}
    found = []
    for c in hits:
        if c.get("element_type") != "text" or counts[section(c)] != 1:
            continue
        for nb in chunks().find(
            {"document_id": c["document_id"], "seq": {"$in": [c["seq"] - 1, c["seq"] + 1]}},
            {"embedding": 0},
        ):
            if nb["_id"] not in have:
                have.add(nb["_id"])
                found.append({**nb, "_is_neighbour": True})
    return found


def _same_place(a: dict, b: dict) -> bool:
    return a.get("document_id") == b.get("document_id") and a.get("page") == b.get("page")


def _overlap(a: dict, b: dict) -> float:
    """Text: Jaccard overlap of word sets. Tables: share of rows of the smaller chunk found in the
    other, so row groups that only repeat the header are kept, while a row group inside the
    whole-table chunk counts as a duplicate."""
    if a.get("element_type") in TABLE_TYPES and b.get("element_type") in TABLE_TYPES:
        la, lb = set(a["text"].splitlines()), set(b["text"].splitlines())
        return len(la & lb) / min(len(la), len(lb)) if la and lb else 0.0
    sa, sb = set(a["text"].lower().split()), set(b["text"].lower().split())
    return len(sa & sb) / len(sa | sb) if sa and sb else 0.0
