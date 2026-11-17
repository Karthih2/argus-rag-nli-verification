"""FEVER-NLI health check for the verifier (spec 13): score the fixed 600 pairs and store results.

Run from the repo root: python -m scripts.run_fever_validation
"""

import time
from datetime import datetime, timezone

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from backend.config import settings
from backend.db.client import fever_validations
from backend.verification.nli import nli_scores
from eval.fever_data import load_sample_pairs

ORDER = ["entailment", "neutral", "contradiction"]
KEY_TO_LABEL = {"ent": "entailment", "neu": "neutral", "con": "contradiction"}


def main() -> None:
    pairs = load_sample_pairs()
    start = time.perf_counter()
    scores = nli_scores(list(zip(pairs["premise"], pairs["hypothesis"])))
    seconds = time.perf_counter() - start

    gold = list(pairs["label"])
    pred = [KEY_TO_LABEL[max(s, key=s.get)] for s in scores]
    report = classification_report(gold, pred, labels=ORDER, output_dict=True, zero_division=0)
    result = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "model": settings.NLI_MODEL_NAME,
        "n_pairs": len(gold),
        "accuracy": round(accuracy_score(gold, pred), 4),
        "macro_f1": round(report["macro avg"]["f1-score"], 4),
        "per_label": {
            lab: {k: round(report[lab][k], 4) for k in ("precision", "recall", "f1-score")} for lab in ORDER
        },
        "confusion_matrix": confusion_matrix(gold, pred, labels=ORDER).tolist(),
        "latency_ms_per_pair": round(seconds / len(gold) * 1000, 1),
    }
    fever_validations().insert_one(dict(result))
    print(
        f"accuracy={result['accuracy']} macro_f1={result['macro_f1']} "
        f"latency={result['latency_ms_per_pair']} ms/pair"
    )
    for lab in ORDER:
        print(f"  {lab:14s} {result['per_label'][lab]}")
    print(f"  confusion (rows=gold, cols=pred, order {ORDER}): {result['confusion_matrix']}")


if __name__ == "__main__":
    main()
