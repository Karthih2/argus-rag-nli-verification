"""Answer drafting fallbacks (fake LLM, no network)."""

from backend.generation import answer


def fake_llm(reply):
    return lambda messages, **kw: {**reply, "_model": "fake"}


def test_answer_without_claims_becomes_sentence_claims(monkeypatch):
    monkeypatch.setattr(answer, "call_llm", fake_llm({"answer": "Records are kept 7 years. Then destroyed.",
                                                      "claims": [], "not_found": False}))
    out = answer.generate_answer("q", "ctx")
    assert not out.not_found and [c.text for c in out.claims] == ["Records are kept 7 years.", "Then destroyed."]


def test_not_found_is_kept(monkeypatch):
    monkeypatch.setattr(answer, "call_llm", fake_llm({"answer": "", "claims": [], "not_found": True}))
    assert answer.generate_answer("q", "ctx").not_found


def test_empty_answer_without_claims_is_not_found(monkeypatch):
    monkeypatch.setattr(answer, "call_llm", fake_llm({"answer": "", "claims": [], "not_found": False}))
    assert answer.generate_answer("q", "ctx").not_found


def test_cites_are_normalised():
    from backend.generation.schemas import Claim

    assert Claim(text="x", cites="[C1], C2").cites == ["C1", "C2"]
    assert Claim(text="x", cites=["[c3]", "C3"]).cites == ["C3"]
    assert Claim(text="x", cites=None).cites == []
