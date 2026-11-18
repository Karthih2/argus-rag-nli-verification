"""Gate behaviour with a fake NLI model (no models, no network)."""

from backend.generation.schemas import AnswerOutput, Claim
from backend.verification import gate

T = {"tau_accept": 0.8, "tau_low": 0.6, "tau_block": 0.7}
TEXT = "Records of complaints are kept on file. Destroy 7 years after case is closed."
EVIDENCE = [{"_id": "c1", "_ref": "C1", "_rerank_score": 0.9, "page": 36, "text": TEXT}]
SUPPORTS = {"ent": 0.95, "neu": 0.04, "con": 0.01}
CONTRADICTS = {"ent": 0.02, "neu": 0.08, "con": 0.9}


def fake_nli(scores):
    return lambda pairs, temperature=1.0: [scores] * len(pairs)


def draft(text, quote="Destroy 7 years after case is closed"):
    return AnswerOutput(answer=text, claims=[Claim(text=text, cites=["C1"], quote=quote)], model="m")


def test_accept_has_full_nli_split_and_highlight(monkeypatch):
    monkeypatch.setattr(gate, "nli_scores", fake_nli(SUPPORTS))
    out = gate.run_gate(draft("Kept 7 years after closure."), EVIDENCE, 1.0, T)
    claim = out["claims"][0]
    assert out["decision"] == "ACCEPT" and out["answer"]
    assert claim["scores"] == {"entailment": 0.95, "neutral": 0.04, "contradiction": 0.01}
    assert claim["highlight"]["span"] is not None


def test_sentence_window_gives_support_when_whole_chunk_is_neutral(monkeypatch):
    def nli(pairs, temperature=1.0):
        return [SUPPORTS if premise != TEXT else {"ent": 0.1, "neu": 0.85, "con": 0.05} for premise, _ in pairs]

    monkeypatch.setattr(gate, "nli_scores", nli)
    out = gate.run_gate(draft("Kept 7 years after closure."), EVIDENCE, 1.0, T)
    assert out["claims"][0]["support"] == 0.95 and out["decision"] == "ACCEPT"


def test_block_shows_evidence_not_draft(monkeypatch):
    monkeypatch.setattr(gate, "nli_scores", fake_nli(CONTRADICTS))
    out = gate.run_gate(draft("Kept 9 years."), EVIDENCE, 1.0, T)
    assert out["decision"] == "BLOCK" and out["answer"] == ""
    assert out["blocked_reason"]["page"] == 36 and "Destroy 7 years" in out["blocked_reason"]["evidence_text"]


def test_number_mismatch_is_unverified(monkeypatch):
    monkeypatch.setattr(gate, "nli_scores", fake_nli(SUPPORTS))
    out = gate.run_gate(draft("Kept 9 years."), EVIDENCE, 1.0, T)
    assert out["claims"][0]["label"] == "UNVERIFIED" and out["decision"] == "WARN"


def test_not_found_is_no_support():
    out = gate.run_gate(AnswerOutput(answer="", not_found=True), EVIDENCE, 1.0, T)
    assert out["decision"] == "NO_SUPPORT" and out["claims"] == []


def test_claim_without_quote_or_citation_is_anchored_to_the_entailing_sentence(monkeypatch):
    def nli(pairs, temperature=1.0):
        neutral = {"ent": 0.3, "neu": 0.65, "con": 0.05}
        return [SUPPORTS if p.startswith("Destroy") else neutral for p, _ in pairs]

    monkeypatch.setattr(gate, "nli_scores", nli)
    claim = Claim(text="Records must be kept for 7 years once a case has ended.")
    out = gate.run_gate(AnswerOutput(answer=claim.text, claims=[claim]), EVIDENCE, 1.0, T)
    c = out["claims"][0]
    assert c["label"] == "SUPPORTED" and out["decision"] == "ACCEPT"
    assert c["cites"] == ["C1"] and c["checks"]["quote_source"] == "verifier" and "Destroy 7 years" in c["quote"]


def test_wrong_number_is_never_anchored(monkeypatch):
    monkeypatch.setattr(gate, "nli_scores", fake_nli(SUPPORTS))
    out = gate.run_gate(AnswerOutput(answer="x", claims=[Claim(text="Destroyed after 9 years.")]), EVIDENCE, 1.0, T)
    assert out["claims"][0]["label"] == "UNVERIFIED"
