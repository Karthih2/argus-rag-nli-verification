"""Load BGE, reranker and NLI models once; shared by everything."""

import logging
import os
from functools import lru_cache

from backend.config import settings

# Must be set before transformers / sentence-transformers are imported.
os.environ.setdefault("HF_HOME", settings.HF_HOME)

import numpy as np  # noqa: E402
from sentence_transformers import CrossEncoder, SentenceTransformer  # noqa: E402

log = logging.getLogger(__name__)

BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    """BGE embedding model, loaded once."""
    log.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
    return SentenceTransformer(settings.EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    """BGE reranker, loaded once."""
    log.info("Loading reranker: %s", settings.RERANKER_MODEL)
    return CrossEncoder(settings.RERANKER_MODEL)


@lru_cache(maxsize=1)
def get_nli_model():
    """DeBERTa NLI model + tokenizer, loaded once."""
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    log.info("Loading NLI model: %s (device=%s)", settings.NLI_MODEL_NAME, device)
    tokenizer = AutoTokenizer.from_pretrained(settings.NLI_MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(settings.NLI_MODEL_NAME)
    model.eval().to(device)
    return model, tokenizer


def preload_models() -> None:
    """Load every model up front (API startup) so the first question isn't slow."""
    get_embedder()
    get_reranker()
    get_nli_model()


def models_loaded() -> dict:
    """Which models are already in memory (for /api/health)."""
    return {
        "embedder": get_embedder.cache_info().currsize > 0,
        "reranker": get_reranker.cache_info().currsize > 0,
        "nli": get_nli_model.cache_info().currsize > 0,
    }


def embed_texts(texts: list[str], is_query: bool = False) -> np.ndarray:
    """Embed texts with BGE. Queries get the instruction prefix. Returns L2-normalised vectors."""
    if is_query:
        texts = [BGE_QUERY_PREFIX + t for t in texts]
    vectors = get_embedder().encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vectors, dtype=np.float32)


def rerank_scores(query: str, passages: list[str]) -> list[float]:
    """Cross-encoder relevance score for each (query, passage) pair."""
    if not passages:
        return []
    scores = get_reranker().predict([(query, p) for p in passages], show_progress_bar=False)
    return [float(s) for s in scores]
