from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

#CONNECTION
def get_client():
    return MongoClient(os.getenv("MONGO_URI"))

def get_db():
    client = get_client()
    return client[os.getenv("DB_NAME", "argus_db")]

#COLLECTIONS
def get_chunks_collection():
    return get_db()["chunks"]

def get_documents_collection():
    return get_db()["documents"]

def get_query_logs_collection():
    return get_db()["query_logs"]

#INDEX SETUP
def create_indexes():
    chunks = get_chunks_collection()

    # Unique chunk identifier
    chunks.create_index("chunk_id", unique=True)

    # Fast filtering
    chunks.create_index("domain")
    chunks.create_index("document_id")

    # Nested fields
    chunks.create_index("metadata.chunk_index")
    chunks.create_index("source.page")

    # Optional: text search (for debugging / fallback)
    chunks.create_index([("text", "text")])

    print("✅ MongoDB indexes created successfully")