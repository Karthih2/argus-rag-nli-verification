"""Create the NASA demo dataset, ingest its PDFs, and print extraction reports.

Run from the repo root:
    python -m scripts.seed_demo            # ingest new PDFs only
    python -m scripts.seed_demo --fresh    # delete the dataset's documents first (full re-ingest)
"""

import argparse
import logging

from backend.config import ROOT_DIR
from backend.db.client import datasets, documents, queries, sessions
from backend.db.indexes import ensure_all_indexes
from backend.ingestion.pipeline import ingest_document
from backend.library import create_dataset, delete_document

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

DATASET_ID = "ds_nasa"
NASA_DIR = ROOT_DIR / "data" / "samples" / "nasa"


def main() -> None:
    args = _args()
    ensure_all_indexes()
    if not datasets().find_one({"_id": DATASET_ID}):
        create_dataset(
            "NASA policies and reports", "Demo and test dataset (US government works)", dataset_id=DATASET_ID
        )
    # Public visitors can read the demo but not upload to it or delete from it.
    datasets().update_one({"_id": DATASET_ID}, {"$set": {"settings.read_only": True}})
    if args.fresh:
        for doc in documents().find({"dataset_id": DATASET_ID}):
            delete_document(doc)
        for coll in (sessions, queries):
            coll().delete_many({"dataset_id": DATASET_ID})

    for pdf in sorted(NASA_DIR.glob("*.pdf")):
        print(f"\n--- {pdf.name}")
        doc = ingest_document(pdf, DATASET_ID)
        print("  skipped (already ingested)" if doc is None else _report(doc))


def _args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fresh", action="store_true", help="delete existing documents first")
    return p.parse_args()


def _report(doc: dict) -> str:
    s = doc.get("stats", {})
    lines = [
        f"  title:  {doc['metadata'].get('title')}  ({doc['metadata'].get('page_count')} pages)",
        f"  chunks: {s.get('chunks')}  tables: {s.get('tables')}  charts: {s.get('charts')}  "
        f"photos: {s.get('photos')}  quotes: {s.get('quotes')}",
        f"  pages by kind: {s.get('pages_by_kind')}",
    ]
    if s.get("empty_pages"):
        lines.append(f"  pages with no chunks: {s['empty_pages']}")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
