"""DeBERTa NLI: batched logits, temperature-scaled probabilities, label order from the model."""

import logging
from functools import lru_cache

import numpy as np
import torch

from backend.config import settings
from backend.models import get_nli_model

log = logging.getLogger(__name__)

LABEL_KEYS = {"entailment": "ent", "neutral": "neu", "contradiction": "con"}


@lru_cache(maxsize=1)
def label_indices() -> dict[str, int]:
    """{'entailment': i, 'neutral': j, 'contradiction': k} read from config.id2label."""
    model, _ = get_nli_model()
    out = {}
    for idx, name in model.config.id2label.items():
        name = name.lower()
        key = "entailment" if "entail" in name else "contradiction" if "contra" in name else "neutral"
        out[key] = int(idx)
    return out


def _fit_premise(text: str, tokenizer) -> str:
    """Premise cut to NLI_MAX_PREMISE_TOKENS so premise + claim fit 512 tokens; warns when cut."""
    ids = tokenizer.encode(text, add_special_tokens=False)
    if len(ids) <= settings.NLI_MAX_PREMISE_TOKENS:
        return text
    log.warning("NLI premise cut from %d to %d tokens", len(ids), settings.NLI_MAX_PREMISE_TOKENS)
    return tokenizer.decode(ids[: settings.NLI_MAX_PREMISE_TOKENS])


def nli_logits(pairs: list[tuple[str, str]]) -> np.ndarray:
    """Raw (N, 3) logits for (premise, hypothesis) pairs."""
    if not pairs:
        return np.empty((0, 3), dtype=np.float32)
    model, tokenizer = get_nli_model()
    device = next(model.parameters()).device
    out = []
    for start in range(0, len(pairs), settings.NLI_BATCH_SIZE):
        batch = pairs[start : start + settings.NLI_BATCH_SIZE]
        inputs = tokenizer(
            [_fit_premise(p, tokenizer) for p, _ in batch],
            [h for _, h in batch],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}
        with torch.no_grad():
            out.append(model(**inputs).logits.cpu().numpy())
    return np.concatenate(out)


def probs_from_logits(logits: np.ndarray, temperature: float = 1.0) -> list[dict]:
    """[{ent, neu, con}] per row: softmax(logits / T)."""
    z = logits / temperature
    probs = np.exp(z - z.max(axis=1, keepdims=True))
    probs /= probs.sum(axis=1, keepdims=True)
    idx = label_indices()
    return [{LABEL_KEYS[name]: float(row[i]) for name, i in idx.items()} for row in probs]


def nli_scores(pairs: list[tuple[str, str]], temperature: float = 1.0) -> list[dict]:
    """[{ent, neu, con}] per (premise, hypothesis) pair, temperature-scaled."""
    return probs_from_logits(nli_logits(pairs), temperature)
