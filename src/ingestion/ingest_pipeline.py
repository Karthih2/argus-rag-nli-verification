import os
import uuid
from src.ingestion.pdf_loader import load_pdf
from src.ingestion.cleaner import clean_text
from src.ingestion.chunker import chunk_text
from db.mongodb import get_chunks_collection

# Root folder
DATA_PATH = "data/raw_documents"

def process_domain(domain_name):
    """
    domain_name = 'nasa' or 'anime'
    """
    domain_path = os.path.join(DATA_PATH, domain_name)
    collection = get_chunks_collection()

    all_chunks = []

    for file in os.listdir(domain_path):

        if not file.endswith(".pdf"):
            continue

        file_path = os.path.join(domain_path, file)
        document_id = str(uuid.uuid4())

        print(f"Processing: {file}")

        # 1. Load PDF
        pages = load_pdf(file_path)

        # 2. Clean text
        for page in pages:
            page["text"] = clean_text(page["text"])

        # 3. Chunk
        chunks = chunk_text(pages)

        # 4. Attach metadata
        for chunk in chunks:
            chunk_record = {
                "chunk_id": str(uuid.uuid4()),
                "document_id": document_id,
                "domain": domain_name,  #  prevents mixing chunks from different domains
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
            }

            all_chunks.append(chunk_record)

    # 5. Store in MongoDB (bulk insert)
    if all_chunks:
        collection.insert_many(all_chunks, ordered=False)
        print(f"Inserted {len(all_chunks)} chunks for {domain_name}")



if __name__ == "__main__":
    process_domain("nasa")
    process_domain("anime")