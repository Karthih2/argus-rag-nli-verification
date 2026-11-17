"""BGE embeddings for chunks (stored as BSON float32 vectors) and for queries."""

from bson.binary import Binary, BinaryVectorDtype

from backend.models import embed_texts


def embed_for_storage(texts: list[str]) -> list[Binary]:
    """Embed passage texts and return BSON BinData float32 vectors."""
    if not texts:
        return []
    return [Binary.from_vector(v.tolist(), BinaryVectorDtype.FLOAT32) for v in embed_texts(texts)]


def embed_query(question: str) -> list[float]:
    """Embed a query with the BGE instruction prefix."""
    return embed_texts([question], is_query=True)[0].tolist()
