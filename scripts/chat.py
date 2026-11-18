"""CLI chat over the NASA demo dataset, printing per-claim verdicts and latency.

Run from the repo root: python -m scripts.chat
"""

import logging
import sys

from backend.db.client import documents
from backend.pipeline import run_question
from backend.sessions import create_session, get_session

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

DATASET_ID = "ds_nasa"
SYMBOL = {"SUPPORTED": "+", "WEAKLY_SUPPORTED": "~", "UNVERIFIED": "?", "CONTRADICTED": "X"}


def main() -> None:
    doc_ids = [d["_id"] for d in documents().find({"dataset_id": DATASET_ID, "processing.status": "ready"})]
    if not doc_ids:
        sys.exit(f"No ready documents in {DATASET_ID}. Run: python -m scripts.seed_demo")
    session_id = create_session(DATASET_ID, doc_ids)["_id"]
    print(f"Argus chat | {len(doc_ids)} documents | empty line or 'quit' to exit\n")
    while (question := _ask()) not in ("", "quit", "exit"):
        try:
            result = run_question(question, DATASET_ID, doc_ids, get_session(session_id))
        except Exception as e:  # noqa: BLE001 - keep the chat alive after one failed question
            print(f"  Error: {e}\n")
            continue
        _print(result)


def _ask() -> str:
    try:
        return input("Q: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""


def _print(r: dict) -> None:
    trust = "-" if r["trust"] is None else r["trust"]
    print(f"\n  [{r['decision']}] trust={trust}")
    if r["blocked_reason"]:
        b = r["blocked_reason"]
        print(f"  WITHHELD. Draft said: {b['draft_claim']}\n  p.{b['page']} says: {b['evidence_text'][:200]}")
    elif r["answer"]:
        print(f"\n  {r['answer']}\n")
    for i, c in enumerate(r["claims"], 1):
        s = c["scores"]
        notes = [n for n, bad in (("no quote", not c["checks"]["quote_match"]),
                                  (c["checks"]["number_detail"], not c["checks"]["numbers_ok"])) if bad]
        print(f"  [{SYMBOL[c['label']]}] {i}. {c['text'][:100]}")
        print(f"       ent={s['entailment']:.2f} neu={s['neutral']:.2f} con={s['contradiction']:.2f} "
              f"p.{c['highlight'].get('page', '?')} {'(' + ', '.join(notes) + ')' if notes else ''}")
    for e in r["evidence"]:
        print(f"    {e['ref']}: {e['file_name']} p.{e['page']} ({e['type']}) rerank={e['rerank']:.2f}")
    print(f"  latency ms: {r['latency_ms']}\n")


if __name__ == "__main__":
    main()
