#src/verification/decision_gate.py

def decide_action(label: str, confidence: float) -> str:

    if label == "entailment" and confidence >= 0.75:
        return "ACCEPT"

    if label == "contradiction":
        return "BLOCK"

    if label == "neutral":
        return "WARN"

    if confidence < 0.5:
        return "RETRY"

    return "WARN"