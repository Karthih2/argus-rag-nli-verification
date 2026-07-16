# src/ingestion/ingest_pipeline.py


import os
import uuid

from ingestion.loaders.pdf_loader import load_pdf
from src.ingestion.cleaner import clean_text
from src.ingestion.chunker import chunk_text
from src.ingestion.chunk_filter import is_good_chunk
from db.mongodb import get_chunks_collection

DATA_PATH = "data/raw_documents"


def process_domain(domain_name: str):
    domain_path = os.path.join(DATA_PATH, domain_name)
    collection = get_chunks_collection()

    all_chunks = []

    print(f"\nProcessing domain: {domain_name}\n")

    for file in os.listdir(domain_path):

        if not file.endswith(".pdf"):
            continue

        file_path = os.path.join(domain_path, file)
        document_id = str(uuid.uuid4())

        print(f"Processing file: {file}")

        # 1. Load PDF
        pages = load_pdf(file_path)

        # 2. Clean text
        for page in pages:
            page["text"] = clean_text(page["text"])

        # 3. Chunk
        chunks = chunk_text(pages)

        # 4. FILTER (CRITICAL STEP)
        chunks = [c for c in chunks if is_good_chunk(c["text"])]

        print(f"   Valid chunks after filtering: {len(chunks)}")

        # 5. Build MongoDB records
        for chunk in chunks:
            all_chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "document_id": document_id,
                "domain": domain_name,
                "file_name": file,
                "text": chunk["text"],
                "source": {
                    "page": chunk["page_number"]
                },
                "metadata": {
                    "chunk_index": chunk["chunk_index"],
                    "chunk_size": 600,
                    "overlap": 120
                }
            })

    # 6. Insert into MongoDB
    if all_chunks:
        collection.insert_many(all_chunks, ordered=False)
        print(f"\nInserted {len(all_chunks)} clean chunks for {domain_name}\n")


if __name__ == "__main__":
    process_domain("nasa")
    process_domain("anime")