"""Background jobs (ingestion), run one at a time so they don't fight over CPU."""

import logging
import shutil
import threading
from pathlib import Path

from backend.ingestion.pipeline import ingest_document

log = logging.getLogger(__name__)

_one_job_at_a_time = threading.Lock()


def ingest_job(pdf_path: Path, dataset_id: str, file_name: str) -> None:
    """Ingest an uploaded document. Deletes the temp upload dir when done."""
    with _one_job_at_a_time:
        try:
            ingest_document(pdf_path, dataset_id, file_name=file_name)
        except Exception:
            log.exception("Ingestion job failed for %s", file_name)
        finally:
            shutil.rmtree(pdf_path.parent, ignore_errors=True)
