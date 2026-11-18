"""Every Groq call: JSON mode, model fallback chain, response cache."""

import hashlib
import json
import logging
from functools import lru_cache

from groq import Groq

from backend.config import ROOT_DIR, settings

log = logging.getLogger(__name__)

CACHE_DIR = ROOT_DIR / "data" / "cache" / "llm"
GROQ_MAX_RETRIES = 5


@lru_cache(maxsize=1)
def _client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set in .env")
    # The SDK waits and retries on rate limits (429) and server errors, with exponential backoff.
    return Groq(api_key=settings.GROQ_API_KEY, max_retries=GROQ_MAX_RETRIES)


def call_llm(
    messages: list[dict],
    json_mode: bool = False,
    reasoning_effort: str | None = "medium",
    use_cache: bool | None = None,
) -> dict | str:
    """Call Groq, trying each model in GROQ_MODELS in order.

    JSON mode returns a dict with the model used under "_model"; text mode returns a string.
    Cached by prompt hash only when LLM_CACHE is on (the eval runner), so evaluation runs are
    repeatable while live answers are always fresh.
    """
    if use_cache is None:
        use_cache = settings.LLM_CACHE
    for model in settings.groq_model_list:
        key = _cache_key(model, messages, json_mode)
        cached = _read_cache(key) if use_cache else None
        if cached is not None:
            return cached if json_mode else cached["_text"]

        kwargs: dict = {"model": model, "messages": messages, "temperature": 0.0}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        try:
            content = _client().chat.completions.create(**kwargs).choices[0].message.content
            if not content:
                raise ValueError("empty response")
            result = {**json.loads(content), "_model": model} if json_mode else {"_text": content}
        except Exception as e:  # noqa: BLE001 - any model failure means "try the next model"
            log.warning("Groq call failed on %s: %s", model, e)
            continue
        if use_cache:
            _write_cache(key, result)
        return result if json_mode else result["_text"]
    raise RuntimeError(f"All Groq models failed: {settings.groq_model_list}")


def _cache_key(model: str, messages: list[dict], json_mode: bool) -> str:
    raw = json.dumps({"model": model, "messages": messages, "json": json_mode}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _read_cache(key: str) -> dict | None:
    path = CACHE_DIR / f"{key}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _write_cache(key: str, result: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{key}.json").write_text(json.dumps(result), encoding="utf-8")
