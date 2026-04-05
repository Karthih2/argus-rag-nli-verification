import re

def clean_text(text):
    text = re.sub(r'\s+', ' ', text)  # remove extra spaces
    text = re.sub(r'\n+', ' ', text)  # remove newlines
    text = text.strip()
    return text