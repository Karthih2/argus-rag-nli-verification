import faiss
import numpy as np
from db.mongodb import get_chunks_collection
from src.retrieval.embedder import Embedder
import pickle
import os

def build_faiss_index(domain="nasa"):

    collection = get_chunks_collection()
    embedder = Embedder()

    # Fetch data
    docs = list(collection.find({"domain": domain}))

    texts = [doc["text"] for doc in docs]
    ids = [doc["chunk_id"] for doc in docs]

    # Encode as passages
    embeddings = embedder.encode(texts, is_query=False)
    embeddings = np.array(embeddings).astype("float32")

    # Normalize (cosine similarity)
    faiss.normalize_L2(embeddings)

    # Use Inner Product
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)

    index.add(embeddings)

    # Ensure folder exists
    os.makedirs("data/embeddings", exist_ok=True)

    # Save index
    faiss.write_index(index, f"data/embeddings/{domain}.index")

    # Save ID mapping
    with open(f"data/embeddings/{domain}_ids.pkl", "wb") as f:
        pickle.dump(ids, f)

    print(f"FAISS index built for {domain}")