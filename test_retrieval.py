from src.retrieval.retriever import Retriever

retriever = Retriever(domain="nasa")

query = "How long is astronaut training?"

results = retriever.retrieve(query)

for i, r in enumerate(results):
    print(f"\n--- Result {i+1} ---")
    print(r["text"][:300])
    print("Page:", r["source"]["page"])