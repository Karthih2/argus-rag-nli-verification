"""MongoDB client and collection accessors."""

import logging

import gridfs
from pymongo import MongoClient
from pymongo.database import Database

from backend.config import settings

log = logging.getLogger(__name__)

_client: MongoClient | None = None
_db: Database | None = None


def get_client() -> MongoClient:
    """Lazy singleton MongoClient."""
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=10_000)
    return _client


def get_db() -> Database:
    """Lazy singleton Database handle."""
    global _db
    if _db is None:
        _db = get_client()[settings.DB_NAME]
    return _db


def get_fs() -> gridfs.GridFS:
    """GridFS for original PDFs."""
    return gridfs.GridFS(get_db(), collection="files")


# Collection accessors
def datasets():
    return get_db()["datasets"]


def documents():
    return get_db()["documents"]


def chunks():
    return get_db()["chunks"]


def sessions():
    return get_db()["sessions"]


def queries():
    return get_db()["queries"]
