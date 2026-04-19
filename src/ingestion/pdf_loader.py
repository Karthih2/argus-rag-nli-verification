import fitz

def load_pdf(file_path: str):
    doc = fitz.open(file_path)
    pages = []

    for i, page in enumerate(doc):
        text = page.get_text("text")

        pages.append({
            "page_number": i + 1,
            "text": text
        })

    return pages