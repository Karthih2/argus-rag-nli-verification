"""Check the setup end to end: .env, MongoDB Atlas, search indexes, Groq, models, and smoke test.

Run from the repo root:
    python -m scripts.check_setup          # basic checks
    python -m scripts.check_setup --smoke  # basic + end-to-end smoke test
"""

import argparse
import logging
import sys
import time

from backend.config import ROOT_DIR, settings

logging.basicConfig(level=logging.WARNING)
OK, FAIL, WARN = "[OK]  ", "[FAIL]", "[WARN]"


# ---------------------------------------------------------------------------
# 1. Environment
# ---------------------------------------------------------------------------

def check_env() -> bool:
    missing = [k for k in ("MONGO_URI", "GROQ_API_KEY") if not getattr(settings, k)]
    if missing:
        print(f"{FAIL} {ROOT_DIR / '.env'}: missing {', '.join(missing)}")
        return False
    print(f"{OK} .env has MONGO_URI and GROQ_API_KEY")
    return True


# ---------------------------------------------------------------------------
# 2. MongoDB: ping, DB, GridFS round-trip, search indexes
# ---------------------------------------------------------------------------

def check_mongodb() -> bool:
    from pymongo.errors import PyMongoError

    from backend.db.client import get_db, get_fs

    ok = True
    try:
        db = get_db()
        db.command("ping")
        print(f"{OK} MongoDB ping: db={settings.DB_NAME}")
    except PyMongoError as e:
        print(f"{FAIL} MongoDB ping: {e}")
        return False

    # GridFS round-trip
    try:
        fs = get_fs()
        test_data = b"argus_check_1kb" * 68  # ~1 KB
        fid = fs.put(test_data, filename="_check_setup_test")
        read_back = fs.get(fid).read()
        fs.delete(fid)
        if read_back != test_data:
            print(f"{FAIL} GridFS: read-back mismatch")
            ok = False
        else:
            print(f"{OK} GridFS put/get/delete round-trip")
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} GridFS: {e}")
        ok = False

    # Search indexes
    if "chunks" not in db.list_collection_names():
        print(f"{WARN} No chunks collection yet; indexes checked after first ingest")
        return ok
    try:
        indexes = {i["name"]: i.get("queryable", False) for i in db.chunks.list_search_indexes()}
        for name in ("chunks_vec", "chunks_text"):
            queryable = indexes.get(name, False)
            status = "queryable" if queryable else "missing or building"
            sym = OK if queryable else WARN
            print(f"{sym} Atlas index {name}: {status}")
            if not queryable:
                ok = False
    except PyMongoError as e:
        print(f"{WARN} Could not list search indexes: {e}")
    return ok


# ---------------------------------------------------------------------------
# 3. Groq: model availability, JSON-mode call, latency
# ---------------------------------------------------------------------------

def check_groq() -> bool:
    from backend.generation.llm import _client, call_llm

    ok = True
    try:
        available = {m.id for m in _client().models.list().data}
        for model in settings.groq_model_list:
            present = model in available
            sym = OK if present else FAIL
            print(f"{sym} Groq model {model}: {'available' if present else 'NOT found'}")
            if not present:
                ok = False

        t0 = time.perf_counter()
        reply = call_llm(
            [{"role": "user", "content": 'Return JSON {"ok": true}.'}],
            json_mode=True,
            reasoning_effort="low",
            use_cache=False,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        json_ok = reply.get("ok") is True
        sym = OK if json_ok else FAIL
        print(f"{sym} Groq JSON call: ok={reply.get('ok')}, model={reply.get('_model')}, {latency_ms}ms")
        if not json_ok:
            ok = False
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} Groq: {e}")
        ok = False
    return ok


# ---------------------------------------------------------------------------
# 4. Models: BGE, reranker, NLI
# ---------------------------------------------------------------------------

def check_models() -> bool:
    ok = True

    # Embedder
    try:
        from backend.models import embed_texts
        vec = embed_texts(["test sentence"])
        dim = vec.shape[1]
        sym = OK if dim == 768 else FAIL
        print(f"{sym} BGE embedder: dim={dim}")
        if dim != 768:
            ok = False
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} BGE embedder: {e}")
        ok = False

    # Reranker
    try:
        from backend.models import rerank_scores
        scores = rerank_scores("test", ["test passage"])
        print(f"{OK} Reranker: score={scores[0]:.4f}")
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} Reranker: {e}")
        ok = False

    # NLI
    try:
        from backend.verification.nli import nli_scores
        result = nli_scores([("The sky is blue.", "The sky has a color.")], temperature=1.0)
        probs = result[0]
        total = sum(probs.values())
        sums_ok = abs(total - 1.0) < 0.01
        sym = OK if sums_ok else FAIL
        print(
            f"{sym} NLI: ent={probs['ent']:.3f}"
            f" neu={probs['neu']:.3f}"
            f" con={probs['con']:.3f} sum={total:.4f}"
        )
        if not sums_ok:
            ok = False
    except Exception as e:  # noqa: BLE001
        print(f"{FAIL} NLI model: {e}")
        ok = False
    return ok


# ---------------------------------------------------------------------------
# 5. Smoke test: ingest, ask, cleanup
# ---------------------------------------------------------------------------

SMOKE_QUESTIONS = [
    "How are astronaut candidates selected?",
    "What training do astronauts undergo?",
    "What are the physical requirements for astronauts?",
]
SMOKE_PDF = ROOT_DIR / "data" / "samples" / "nasa" / "astronaut_selection_and_training.pdf"


def smoke_test() -> bool:
    import shutil
    import tempfile
    from pathlib import Path

    from backend.db.client import chunks, documents
    from backend.ingestion.pipeline import ingest_document
    from backend.library import create_dataset, delete_dataset
    from backend.pipeline import run_question

    if not SMOKE_PDF.exists():
        print(f"{FAIL} Smoke: {SMOKE_PDF} not found")
        return False

    dataset_id = "ds_smoke_test"
    ok = True
    try:
        # Create temp dataset
        create_dataset("Smoke Test", dataset_id=dataset_id)
        print(f"{OK} Smoke: created dataset {dataset_id}")

        # Ingest
        tmp = Path(tempfile.mkdtemp())
        pdf_copy = tmp / SMOKE_PDF.name
        pdf_copy.write_bytes(SMOKE_PDF.read_bytes())
        doc = ingest_document(pdf_copy, dataset_id, file_name=SMOKE_PDF.name, image_reading=False)
        shutil.rmtree(tmp, ignore_errors=True)
        if doc is None:
            print(f"{FAIL} Smoke: ingest returned None (duplicate?)")
            ok = False
        else:
            print(f"{OK} Smoke: ingested {doc['file']['name']}, status={doc['processing']['status']}")

        # Ask questions
        for q in SMOKE_QUESTIONS:
            try:
                result = run_question(q, dataset_id)
                valid = ("ACCEPT", "ACCEPT_LOW_CONFIDENCE", "WARN", "BLOCK", "NO_SUPPORT")
                has_decision = result.get("decision") in valid
                has_trust = isinstance(result.get("trust"), int) and 0 <= result["trust"] <= 100
                has_claims = isinstance(result.get("claims"), list)
                has_evidence = isinstance(result.get("evidence"), list)
                passed = has_decision and has_trust and has_claims and has_evidence
                sym = OK if passed else FAIL
                print(
                    f"{sym} Smoke Q: '{q[:50]}...'"
                    f" decision={result.get('decision')}"
                    f" trust={result.get('trust')}"
                )
                if not passed:
                    ok = False
            except Exception as e:  # noqa: BLE001
                print(f"{FAIL} Smoke Q: '{q[:50]}...' error: {e}")
                ok = False

    finally:
        # Cleanup
        try:
            delete_dataset(dataset_id)
            remaining_chunks = chunks().count_documents({"dataset_id": dataset_id})
            remaining_docs = documents().count_documents({"dataset_id": dataset_id})
            clean = remaining_chunks == 0 and remaining_docs == 0
            sym = OK if clean else FAIL
            status = "complete" if clean else (
                f"incomplete: {remaining_chunks} chunks,"
                f" {remaining_docs} docs left"
            )
            print(f"{sym} Smoke: cleanup {status}")
            if not clean:
                ok = False
        except Exception as e:  # noqa: BLE001
            print(f"{FAIL} Smoke: cleanup error: {e}")
            ok = False
    return ok


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Argus setup check")
    parser.add_argument("--smoke", action="store_true", help="Run end-to-end smoke test")
    args = parser.parse_args()

    print("=== Argus setup check ===\n")
    results = [check_env()]
    if results[0]:
        results.append(check_mongodb())
        results.append(check_groq())
        results.append(check_models())
        if args.smoke:
            print("\n--- Smoke test ---")
            results.append(smoke_test())

    print(f"\n{'All checks passed.' if all(results) else 'Some checks failed (see above).'}")
    sys.exit(0 if all(results) else 1)


if __name__ == "__main__":
    main()
