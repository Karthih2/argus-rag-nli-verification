"""Claim labels and the answer decision."""

SUPPORTED = "SUPPORTED"
WEAK = "WEAKLY_SUPPORTED"
UNVERIFIED = "UNVERIFIED"
CONTRADICTED = "CONTRADICTED"
LABELS = (SUPPORTED, WEAK, UNVERIFIED, CONTRADICTED)
DECISIONS = ("ACCEPT", "ACCEPT_LOW_CONFIDENCE", "WARN", "BLOCK", "NO_SUPPORT")


def label_claim(
    support: float,
    contra: float,
    quote_found: bool,
    quotations_ok: bool,
    numbers_ok: bool,
    thresholds: dict,
) -> str:
    """Rules checked in order; thresholds holds tau_accept, tau_low and tau_block."""
    if not quotations_ok or contra >= thresholds["tau_block"]:
        return CONTRADICTED
    if not numbers_ok:
        return UNVERIFIED
    if support >= thresholds["tau_accept"] and quote_found:
        return SUPPORTED
    if support >= thresholds["tau_low"]:
        return WEAK
    return UNVERIFIED


def decide_answer(labels: list[str], not_found: bool) -> str:
    """Answer-level decision from the claim labels."""
    if not_found or not labels:
        return "NO_SUPPORT"
    if CONTRADICTED in labels:
        return "BLOCK"
    if all(lab == SUPPORTED for lab in labels):
        return "ACCEPT"
    if all(lab in (SUPPORTED, WEAK) for lab in labels):
        return "ACCEPT_LOW_CONFIDENCE"
    return "WARN"


def count_labels(claims: list[dict]) -> dict:
    """{'supported': n, 'weak': n, 'unverified': n, 'contradicted': n} for the score card."""
    names = {SUPPORTED: "supported", WEAK: "weak", UNVERIFIED: "unverified", CONTRADICTED: "contradicted"}
    counts = dict.fromkeys(names.values(), 0)
    for c in claims:
        counts[names[c["label"]]] += 1
    return counts
