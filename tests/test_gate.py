"""Gate behaviour with fake NLI and fake repair (no models, no network)."""

from backend.generation.schemas import AnswerOutput, Claim
from backend.verification import gate

T = {"tau_accept": 0.8, "tau_low": 0.6, "tau_block": 0.7, "tau_rel": 0.0}
EVIDENCE = [
    {
        "_id": "c1",
        "_ref": "C1",
        "_rerank_score": 0.9,
        "page": 36,
        "text": "Records: Destroy 7 years after case is closed.",
    }
]


def fake_nli(scores):
    return lambda pairs, temperature=1.0: [scores] * len(pairs)


def draft(text, quote="Destroy 7 years after case is closed"):
    return AnswerOutput(answer=text, claims=[Claim(text=text, cites=["C1"], quote=quote)], model="m")


def test_accept(monkeypatch):
    monkeypatch.setattr(gate, "nli_scores", fake_nli({"ent": 0.95, "neu": 0.04, "con": 0.01}))
    out = gate.run_gate("q", "ctx", EVIDENCE, draft("Kept 7 years after closure."), 1.0, T)
    assert out["decision"] == "ACCEPT" and not out["repaired"]
    assert out["claims"][0]["highlight"]["span"] is not None


def test_block_is_repaired_once(monkeypatch):
    monkeypatch.setattr(gate, "nli_scores", fake_nli({"ent": 0.02, "neu": 0.08, "con": 0.9}))
    monkeypatch.setattr(gate, "repair_answer", lambda q, c, f: AnswerOutput(answer="", not_found=True))
    out = gate.run_gate("q", "ctx", EVIDENCE, draft("Kept 9 years."), 1.0, T)
    assert out["decision"] == "NO_SUPPORT" and out["answer"] == "" and len(out["attempts"]) == 2


def test_block_shows_evidence_not_draft(monkeypatch):
    monkeypatch.setattr(gate, "nli_scores", fake_nli({"ent": 0.02, "neu": 0.08, "con": 0.9}))
    out = gate.run_gate("q", "ctx", EVIDENCE, draft("Kept 9 years."), 1.0, T, allow_repair=False)
    assert out["decision"] == "BLOCK" and out["answer"] == ""
    assert out["blocked_reason"]["page"] == 36 and "Destroy 7 years" in out["blocked_reason"]["evidence_text"]


def test_number_mismatch_is_unverified(monkeypatch):
    monkeypatch.setattr(gate, "nli_scores", fake_nli({"ent": 0.95, "neu": 0.04, "con": 0.01}))
    out = gate.run_gate("q", "ctx", EVIDENCE, draft("Kept 9 years."), 1.0, T, allow_repair=False)
    assert out["claims"][0]["label"] == "UNVERIFIED" and out["decision"] == "WARN"


def test_repair_that_is_not_better_is_not_used(monkeypatch):
    monkeypatch.setattr(gate, "nli_scores", fake_nli({"ent": 0.95, "neu": 0.04, "con": 0.01}))
    monkeypatch.setattr(gate, "repair_answer", lambda q, c, f: draft("Kept 11 years."))
    out = gate.run_gate("q", "ctx", EVIDENCE, draft("Kept 9 years."), 1.0, T)
    assert out["decision"] == "WARN" and not out["repaired"] and len(out["attempts"]) == 2
    assert out["claims"][0]["text"] == "Kept 9 years."
