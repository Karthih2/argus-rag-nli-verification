"""All LLM prompts in one place: answers and context formatting."""

from backend.common.text import evidence_text

_JSON_SHAPE = 'Return valid JSON with keys: answer, claims (array of {"text", "cites", "quote"}), not_found.'

ANSWER_SYSTEM = f"""You answer questions using ONLY the numbered context below. Rules:
1. Write one concise paragraph as "answer".
2. Break the answer into "claims", each stating ONE fact from the answer.
3. Each claim cites the context chunk it comes from, such as "C1", and copies a short verbatim
   "quote" (one sentence or table row) from that chunk.
   Chunks marked N1, N2, ... are surrounding context only and must not be cited.
4. Copy numbers, names and dates exactly as written in the source.
5. If any chunk answers the question, even partly, answer with what the context says.
   Set "not_found": true (and leave claims empty) only when no chunk is about the question.

{_JSON_SHAPE}"""

ANSWER_USER = """Context:
{context}

Question: {question}

Return JSON only."""

# Added on the one retry after a "not found" draft when retrieval found a strongly relevant passage.
RETRY_NOTE = """

Note: the top-ranked chunks were judged relevant to this question. Read them again carefully and
answer from them. Use "not_found" only if they really do not address the question."""


def format_context(evidence: list[dict]) -> str:
    """Numbered context for the prompt, with file, page and type for each chunk."""
    parts = []
    for c in evidence:
        tags = [f"{c.get('file_name', '')} p.{c.get('page', '?')}", c.get("element_type", "text")]
        if c.get("_is_neighbour"):
            tags.append("context only, do not cite")
        parts.append(f"[{c['_ref']}] ({', '.join(tags)})\n{evidence_text(c)}")
    return "\n\n".join(parts)
