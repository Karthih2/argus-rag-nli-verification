"""GET /api/health: database, search indexes and models."""

from fastapi import APIRouter
from pymongo.errors import PyMongoError

from backend.db.client import chunks, get_db
from backend.models import models_loaded

router = APIRouter(tags=["health"])
SEARCH_INDEXES = ("chunks_vec", "chunks_text")


@router.get("/health")
def health():
    checks: dict = {"models": models_loaded()}
    try:
        get_db().command("ping")
        checks["database"] = "ok"
        ready = {i["name"]: i.get("queryable", False) for i in chunks().list_search_indexes()}
        checks["indexes"] = {name: "ready" if ready.get(name) else "missing" for name in SEARCH_INDEXES}
    except PyMongoError as e:
        checks["database"] = f"error: {e}"
    ok = checks["database"] == "ok" and all(v == "ready" for v in checks.get("indexes", {}).values())
    return {"status": "ok" if ok else "degraded", "checks": checks}
