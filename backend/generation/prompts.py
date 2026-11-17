"""All LLM prompts in one place: answers and context formatting."""

from backend.common.text import evidence_text

_JSON_SHAPE = 'Return valid JSON with keys: answer, claims (array of {"text", "cites", "quote"}), not_found.'

ANSWER_SYSTEM = f"""You answer questions using ONLY the numbered context below. Rules:
1. Write one concise paragraph as "answer".
2. Break the answer into "claims", each stating ONE fact.
3. Each claim cites a context chunk such as "C1" and copies a verbatim "quote" from it.
   Chunks marked N1, N2, ... are surrounding context only and must not be cited.
4. Copy numbers exactly as written in the source.
5. If the context does not answer the question, set "not_found": true and leave claims empty.

{_JSON_SHAPE}"""

ANSWER_USER = """Context:
{context}

Question: {question}

Return JSON only."""


def format_context(evidence: list[dict]) -> str:
    """Numbered context for the prompt, with file, page and type for each chunk."""
    parts = []
    for c in evidence:
        tags = [f"{c.get('file_name', '')} p.{c.get('page', '?')}", c.get("element_type", "text")]
        if c.get("_is_neighbour"):
            tags.append("context only, do not cite")
        parts.append(f"[{c['_ref']}] ({', '.join(tags)})\n{evidence_text(c)}")
    return "\n\n".join(parts)
