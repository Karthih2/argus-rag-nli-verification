# src/verification/hallucination_checker.py
from .nli_model import NLIModel


class HallucinationChecker:

    def __init__(self):
        self.nli = NLIModel()

    def verify(self, answer_json: dict, chunks: list):

        hypothesis = answer_json.get("answer", "").strip()

        if not hypothesis:
            return "unknown", 0.0, {}

        if hypothesis.lower() == "not found in document":
            return "no_support", 0.0, {}

        results = []

        # 🔥 FIX: use more evidence (TOP 5 instead of 3)
        for rank, chunk in enumerate(chunks[:5], start=1):

            premise = chunk["text"]

            label, confidence, scores = self.nli.predict(
                premise=premise,
                hypothesis=hypothesis
            )

            results.append({
                "rank": rank,
                "label": label,
                "confidence": confidence,
                "chunk_text": premise[:250]
            })

        # 🔥 CRITICAL FIX: contradiction override
        for r in results:
            if r["label"] == "contradiction" and r["confidence"] > 0.75:
                return "contradiction", r["confidence"], {"raw_results": results}

        # best match logic
        best = max(results, key=lambda x: x["confidence"])

        if best["label"] == "entailment" and best["confidence"] >= 0.75:
            return "entailment", best["confidence"], {"raw_results": results}

        if best["label"] == "neutral":
            return "neutral", best["confidence"], {"raw_results": results}

        return "unknown", best["confidence"], {"raw_results": results}