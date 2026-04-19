import re


def is_valid_sentence(s):

    s = s.strip()

    # too short or noisy
    if len(s) < 40:
        return False

    # reject table-like text
    if sum(c.isdigit() for c in s) > len(s) * 0.3:
        return False

    # reject pure numeric lines
    if len(s.split()) < 6:
        return False

    return True


def extract_evidence(chunks, answer_text, top_k=5):

    sentences = []

    for c in chunks:
        text = c.get("text", "")
        split = re.split(r'(?<=[.!?])\s+', text)

        for s in split:
            if is_valid_sentence(s):
                sentences.append(s)

    answer_words = set(answer_text.lower().split())

    scored = []

    for s in sentences:
        words = set(s.lower().split())

        overlap = len(answer_words.intersection(words))

        # stricter threshold (IMPORTANT FIX)
        if overlap >= 3:
            scored.append((overlap, s))

    scored.sort(reverse=True, key=lambda x: x[0])

    return [
        {"sentence": s, "score": sc}
        for sc, s in scored[:top_k]
    ]