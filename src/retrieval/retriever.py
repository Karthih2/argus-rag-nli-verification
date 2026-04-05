import faiss
import pickle
import numpy as np
from src.retrieval.embedder import Embedder
from db.mongodb import get_chunks_collection

class Retriever:
    def __init__(self, domain="nasa"):
        self.embedder = Embedder()
        self.collection = get_chunks_collection()

        # Load FAISS index
        self.index = faiss.read_index(f"data/embeddings/{domain}.index")

        # Load ID mapping
        with open(f"data/embeddings/{domain}_ids.pkl", "rb") as f:
            self.ids = pickle.load(f)

    def retrieve(self, query, top_k=5):

        # Encode as query
        query_vec = self.embedder.encode([query], is_query=True)
        query_vec = np.array(query_vec).astype("float32")

        # Normalize query
        faiss.normalize_L2(query_vec)

        distances, indices = self.index.search(query_vec, top_k)

        results = []

        for idx in indices[0]:
            chunk_id = self.ids[idx]
            doc = self.collection.find_one({"chunk_id": chunk_id})
            results.append(doc)

        return results