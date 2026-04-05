from sentence_transformers import SentenceTransformer

class Embedder:
    def __init__(self):
        self.model = SentenceTransformer(
            "BAAI/bge-base-en-v1.5",
            device="cpu"
        )

    def encode(self, texts, is_query=False):
        if is_query:
            texts = [f"query: {t}" for t in texts]
        else:
            texts = [f"passage: {t}" for t in texts]

        return self.model.encode(texts, show_progress_bar=True)