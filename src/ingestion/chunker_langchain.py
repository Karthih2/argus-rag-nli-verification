from langchain_text_splitters import RecursiveCharacterTextSplitter


class SmartChunker:

    def __init__(self, chunk_size=800, overlap=120):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=overlap,
            separators=["\n\n", "\n", ".", " "]
        )

    def chunk_text(self, pages):

        chunks = []

        for page in pages:

            text = page.get("text", "")
            page_number = page.get("page_number", 0)

            splits = self.splitter.split_text(text)

            for i, chunk in enumerate(splits):

                chunks.append({
                    "text": chunk,
                    "page_number": page_number,
                    "chunk_index": i,
                    "has_numbers": bool(re.search(r"\d+", chunk))
                })

        return chunks