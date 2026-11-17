"""FastAPI app: /api routes plus the built React frontend at /.

Run from the repo root: uvicorn backend.main:app --reload
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import (
    analytics,
    ask,
    datasets,
    documents,
    health,
    pages,
    queries,
    sessions,
)
from backend.config import ROOT_DIR, settings
from backend.db.indexes import ensure_all_indexes
from backend.models import preload_models

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger(__name__)

FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Create indexes and load models once at startup."""
    ensure_all_indexes()
    if os.getenv("ARGUS_LAZY_MODELS") != "1":
        preload_models()
    yield


app = FastAPI(title="Argus", version="0.3.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)
for module in (health, datasets, documents, sessions, ask, queries, analytics, pages):
    app.include_router(module.router, prefix="/api")

# Serve the built UI only when `npm run build` has produced it.
if (FRONTEND_DIST / "index.html").exists() and (FRONTEND_DIST / "static").is_dir():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIST / "static"), name="frontend-static")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        """Built files as they are; any other path gets index.html so app routes survive a reload."""
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        file = (FRONTEND_DIST / path).resolve()
        inside = file.is_relative_to(FRONTEND_DIST.resolve())
        return FileResponse(file if path and inside and file.is_file() else FRONTEND_DIST / "index.html")
