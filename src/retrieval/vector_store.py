# src/retrieval/vector_store.py

import faiss
import numpy as np
import pickle
import os

from db.mongodb import get_chunks_collection
from src.retrieval.embedder import Embedder


def build_faiss_index(domain="anime"):
    collection = get_chunks_collection()
    embedder = Embedder()

    print("\n[STEP 1] Fetching data from MongoDB...")

    docs = list(collection.find({"domain": domain}))
    print("[DEBUG] docs found:", len(docs))

    if len(docs) == 0:
        raise ValueError(f"No documents found for domain: {domain}. Run ingestion first.")

    texts = [doc.get("text", "") for doc in docs]
    ids = [doc.get("chunk_id") for doc in docs]

    if len(texts) == 0:
        raise ValueError("No valid text found in documents.")

    print("\n[STEP 2] Generating embeddings...")

    embeddings = embedder.encode(texts, is_query=False)
    embeddings = np.array(embeddings).astype("float32")

    print("[DEBUG] embeddings shape:", embeddings.shape)

    if embeddings.ndim != 2 or embeddings.shape[0] == 0:
        raise ValueError("Invalid embeddings generated.")

    print("\n[STEP 3] Building FAISS index...")

    faiss.normalize_L2(embeddings)

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    print("\n[STEP 4] Saving index...")

    os.makedirs("data/embeddings", exist_ok=True)

    faiss.write_index(index, f"data/embeddings/{domain}.index")

    with open(f"data/embeddings/{domain}_ids.pkl", "wb") as f:
        pickle.dump(ids, f)

    print("\n[SUCCESS] FAISS index built successfully")
    print("Vectors indexed:", len(ids))


# 🔥 IMPORTANT: ENTRY POINT FIX
if __name__ == "__main__":
    build_faiss_index("anime")