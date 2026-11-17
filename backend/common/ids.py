"""ID creation for all record types."""

import hashlib
import uuid


def make_id(prefix: str) -> str:
    """Short random ID with type prefix (e.g. ds_, doc_, c_, a_, s_, q_)."""
    return f"{prefix}{uuid.uuid4().hex[:12]}"


def chunk_id(document_id: str, element_path: str) -> str:
    """Deterministic chunk ID, unique per document (the same PDF may sit in several datasets)."""
    raw = f"{document_id}:{element_path}"
    return "c_" + hashlib.sha1(raw.encode()).hexdigest()[:20]


def file_sha256(data: bytes) -> str:
    """SHA-256 hex digest of file contents."""
    return hashlib.sha256(data).hexdigest()
