from db.mongodb import get_chunks_collection

def run_checks():
    col = get_chunks_collection()

    print("\n🔍 ===== MONGODB VERIFICATION =====\n")

    # 1. Total count
    total = col.count_documents({})
    print(f"📊 Total chunks: {total}")

    # 2. Domain counts
    nasa = col.count_documents({"domain": "nasa"})
    anime = col.count_documents({"domain": "anime"})

    print(f"🚀 NASA chunks: {nasa}")
    print(f"🎌 Anime chunks: {anime}")

    # 3. Sample document
    print("\n📄 Sample Document:")
    sample = col.find_one()
    print({
        "chunk_id": sample.get("chunk_id"),
        "domain": sample.get("domain"),
        "file_name": sample.get("file_name"),
        "page": sample.get("source", {}).get("page")
    })

    # 4. Check empty chunks
    empty_chunks = col.count_documents({"text": ""})
    print(f"\n⚠️ Empty chunks: {empty_chunks}")

    # 5. Check duplicate chunk_ids (rare but important)
    pipeline = [
        {"$group": {"_id": "$chunk_id", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}}
    ]
    duplicates = list(col.aggregate(pipeline))
    print(f"🔁 Duplicate chunk_ids: {len(duplicates)}")

    # 6. Chunks per file
    print("\n📁 Chunks per file:")
    pipeline = [
        {"$group": {"_id": "$file_name", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]

    for doc in col.aggregate(pipeline):
        print(f"{doc['_id']} → {doc['count']} chunks")

    # 7. Preview some text
    print("\n🧠 Sample Chunk Text:")
    for doc in col.find().limit(2):
        print("-" * 40)
        print(doc["text"][:200])  # first 200 chars


if __name__ == "__main__":
    run_checks()