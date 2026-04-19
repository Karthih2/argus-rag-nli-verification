# src/retrieval/retriever.py

import re
import faiss
import pickle
import numpy as np

from src.retrieval.embedder import Embedder
from db.mongodb import get_chunks_collection


class Retriever:

    def __init__(self, domain="nasa"):
        self.domain = domain
        self.embedder = Embedder()
        self.collection = get_chunks_collection()

        self.index = faiss.read_index(f"data/embeddings/{domain}.index")

        with open(f"data/embeddings/{domain}_ids.pkl", "rb") as f:
            self.ids = pickle.load(f)

    def _extract_year(self, text: str):
        match = re.search(r"\b(19|20)\d{2}\b", text)
        return match.group() if match else None

    def retrieve(self, query: str, top_k: int = 5) -> list:

        query_vec = self.embedder.encode([query], is_query=True)
        query_vec = np.array(query_vec).astype("float32")
        faiss.normalize_L2(query_vec)

        distances, indices = self.index.search(query_vec, top_k * 5)

        year = self._extract_year(query)
        query_lower = query.lower()

        results = []

        for score, idx in zip(distances[0], indices[0]):

            if idx == -1:
                continue

            chunk_id = self.ids[idx]
            doc = self.collection.find_one({"chunk_id": chunk_id})

            if not doc:
                continue

            text = doc.get("text", "").strip()
            text_lower = text.lower()

            # skip junk chunks
            if len(text) < 40:
                continue

            boost = 0.0

            file_name = doc.get("file_name", "").lower()

            # YEAR BOOST (existing logic)
            if year:
                if year in file_name:
                    boost += 0.3
                if year in text_lower:
                    boost += 0.2

            # KEYWORD BOOST 
            # full phrase match
            if query_lower in text_lower:
                boost += 0.8

            # partial word match
            query_words = query_lower.split()
            word_hits = sum(1 for w in query_words if w in text_lower)

            if word_hits > 0:
                boost += (word_hits / len(query_words)) * 0.4

            # FINAL SCORE
            final_score = float(score) * 0.6 + boost

            results.append((final_score, doc))

        results.sort(key=lambda x: x[0], reverse=True)

        return [doc for _, doc in results[:top_k]]