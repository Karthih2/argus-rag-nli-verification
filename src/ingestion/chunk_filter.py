import re

def is_good_chunk(text: str) -> bool:
    text = text.strip()

    if len(text) < 50:
        return False

    low = text.lower()

    # remove figure/chart noise
    if "figure" in low or "chart" in low:
        return False

    # remove heavy pdf artifacts
    if text.count("█") > 3:
        return False

    # too numeric → likely table garbage
    if len(text) > 0:
        digit_ratio = sum(c.isdigit() for c in text) / len(text)
        if digit_ratio > 0.6:
            return False

    # repetitive junk detection
    if len(set(text)) < 25:
        return False

    # remove pure symbol junk
    if re.fullmatch(r"[\W_]+", text):
        return False

    return True