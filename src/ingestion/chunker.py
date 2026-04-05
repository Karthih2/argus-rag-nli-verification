from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_text(pages, chunk_size=600, overlap=120):
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap
    )

    chunks = []

    for page in pages:
        splits = splitter.split_text(page["text"])

        for i, chunk in enumerate(splits):
            chunks.append({
                "text": chunk,
                "page_number": page["page_number"],
                "chunk_index": i
            })

    return chunks