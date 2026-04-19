from typing import List, Dict


def build_argus_prompt(query: str, chunks: List[Dict]) -> str:
    """
    Build grounded prompt using retrieved chunks.
    """

    context_blocks = []

    for chunk in chunks:
        file_name = chunk.get("file_name", "unknown_file")
        page = chunk.get("source", {}).get("page", "unknown")
        text = chunk.get("text", "")

        context_blocks.append(
            f"[Document: {file_name} | Page: {page}]\n{text}"
        )

    context = "\n\n".join(context_blocks)

    prompt = f"""
You are a strict factual AI assistant.

Rules:
1. Use ONLY the provided context.
2. Do NOT hallucinate.
3. If answer is not directly supported, return "Not found in document".
4. Use wording close to the source when possible.
5. Return ONLY valid JSON.

JSON Format:
{{
  "answer": "One complete factual sentence",
  "evidence": ["Exact supporting sentence"],
  "source": "document_name - page_number",
  "confidence": "High | Medium | Low"
}}

Context:
{context}

Question:
{query}
"""

    return prompt.strip()