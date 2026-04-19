import json
from groq import Groq

from src.config.settings import (
    GROQ_API_KEY,
    MODEL_PRIORITY,
    TEMPERATURE,
    MAX_TOKENS
)


if not GROQ_API_KEY:
    raise ValueError("Missing GROQ_API_KEY in .env")


client = Groq(api_key=GROQ_API_KEY)


def _call_model(model_name: str, prompt: str) -> str:
    """
    Send prompt to Groq model.
    """

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
    )

    return response.choices[0].message.content.strip()


def _safe_parse_json(text: str) -> dict:
    """
    Robust JSON parsing.
    """

    try:
        return json.loads(text)

    except Exception:
        start = text.find("{")
        end = text.rfind("}") + 1

        if start != -1 and end != -1:
            return json.loads(text[start:end])

        raise ValueError("Invalid JSON response from model")


def generate_answer(prompt: str) -> dict:
    """
    Try models in priority order.
    """

    last_error = None

    for model_name in MODEL_PRIORITY:
        try:
            output = _call_model(model_name, prompt)
            parsed = _safe_parse_json(output)
            parsed["model_used"] = model_name
            return parsed

        except Exception as error:
            last_error = error
            continue

    raise RuntimeError(f"All models failed. Last error: {last_error}")