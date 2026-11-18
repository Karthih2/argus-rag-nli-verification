"""FEVER-NLI health check for the verifier: score the fixed 600 pairs, write results/fever_<date>.json.

Run from the repo root: python -m scripts.run_fever_validation
"""

import json
import time
from datetime import datetime, timezone

from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from backend.calibration.trust_model import get_temperature
from backend.config import ROOT_DIR, settings
from backend.verification.nli import nli_scores
from eval.fever_data import load_sample_pairs

ORDER = ["entailment", "neutral", "contradiction"]
KEY_TO_LABEL = {"ent": "entailment", "neu": "neutral", "con": "contradiction"}


def main() -> None:
    pairs = load_sample_pairs()
    start = time.perf_counter()
    scores = nli_scores(list(zip(pairs["premise"], pairs["hypothesis"])), get_temperature())
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
        "per_label": {lab: {k: round(report[lab][k], 4) for k in ("precision", "recall", "f1-score")} for lab in ORDER},
        "confusion_matrix_rows_gold": confusion_matrix(gold, pred, labels=ORDER).tolist(),
        "latency_ms_per_pair": round(seconds / len(gold) * 1000, 1),
    }
    out = ROOT_DIR / "results" / f"fever_{datetime.now(timezone.utc):%Y-%m-%d}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result, indent=2))
    print(f"accuracy={result['accuracy']} macro_f1={result['macro_f1']} "
          f"latency={result['latency_ms_per_pair']} ms/pair -> {out}")


if __name__ == "__main__":
    main()
