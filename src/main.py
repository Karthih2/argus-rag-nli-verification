import json
import time
from pathlib import Path

from src.generation.prompt_template import build_argus_prompt
from src.generation.llm import generate_answer
from src.verification.hallucination_checker import HallucinationChecker
from src.reasoning.evidence_extractor import extract_evidence
from src.retrieval.retriever import Retriever


# -----------------------------
# CONFIG
# -----------------------------
LOG_DIR = Path("logs")
MAX_RETRIES = 2

retriever_cache = {}


# -----------------------------
# RETRIEVER
# -----------------------------
def get_retriever(domain: str):
    if domain not in retriever_cache:
        retriever_cache[domain] = Retriever(domain=domain)
    return retriever_cache[domain]


def retrieve_chunks(query: str, domain: str = "nasa", top_k: int = 5) -> list:

    retriever = get_retriever(domain)
    results = retriever.retrieve(query=query, top_k=top_k)

    chunks = []

    for doc in results:
        chunks.append({
            "text": doc.get("text", ""),
            "file_name": doc.get("file_name", "unknown.pdf"),
            "source": {
                "page": doc.get("source", {}).get("page", "N/A")
            }
        })

    print(f"\nRetrieved chunks: {len(chunks)}")
    return chunks


# -----------------------------
# LOGGING
# -----------------------------
def save_log(data: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    file_path = LOG_DIR / f"log_{int(time.time())}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# -----------------------------
# TRUST SCORE
# -----------------------------
def calculate_trust_score(label: str, confidence: float) -> int:

    if label == "entailment":
        return min(100, round(confidence * 100))

    if label == "weak_support":
        return round(confidence * 75)

    if label == "neutral":
        return round(confidence * 50)

    if label == "contradiction":
        return 0

    return 0


# -----------------------------
# GENERATION + VERIFICATION
# -----------------------------
def generate_verified_answer(query: str, chunks: list, checker):

    final_answer = None
    final_label = "unknown"
    final_confidence = 0.0
    final_debug = {}

    for attempt in range(MAX_RETRIES + 1):

        prompt = build_argus_prompt(query, chunks)
        answer_json = generate_answer(prompt)

        label, confidence, debug = checker.verify(answer_json, chunks)

        final_answer = answer_json
        final_label = label
        final_confidence = confidence
        final_debug = debug

        if label == "entailment" and confidence >= 0.85:
            break

        if attempt < MAX_RETRIES:
            print(f"Retrying generation... ({attempt + 1})")

    return final_answer, final_label, final_confidence, final_debug


# -----------------------------
# MAIN PIPELINE
# -----------------------------
def run_pipeline(query: str, domain: str = "nasa") -> None:

    start_time = time.time()
    checker = HallucinationChecker()

    # 1. Retrieve
    chunks = retrieve_chunks(query=query, domain=domain, top_k=8)

    if not chunks:
        print("No relevant documents found.")
        return

    # 2. Generate + Verify
    answer_json, label, confidence, debug = generate_verified_answer(
        query=query,
        chunks=chunks,
        checker=checker
    )

    # -----------------------------
    # 🔥 EVIDENCE EXTRACTION (FIXED)
    # -----------------------------
    answer_text = (
        answer_json.get("answer", "")
        if isinstance(answer_json, dict)
        else str(answer_json)
    )

    evidence = extract_evidence(chunks, answer_text)

    # -----------------------------
    # METRICS
    # -----------------------------
    latency = round(time.time() - start_time, 2)
    trust_score = calculate_trust_score(label, confidence)

    # -----------------------------
    # LOGGING
    # -----------------------------
    save_log({
        "query": query,
        "domain": domain,
        "retrieved_docs": len(chunks),
        "latency_sec": latency,
        "verdict": label,
        "confidence": round(confidence, 4),
        "trust_score": trust_score
    })

    # -----------------------------
    # OUTPUT
    # -----------------------------
    print("\n" + "=" * 60)
    print("FINAL RESULT")
    print("=" * 60)

    print("Domain      :", domain)
    print("Question    :", query)
    print("Answer      :", answer_text)
    print("Verdict     :", label)
    print("Confidence  :", round(confidence, 4))
    print("Trust Score :", f"{trust_score}/100")
    print("Latency     :", f"{latency} sec")

    # -----------------------------
    # EVIDENCE PRINT
    # -----------------------------
    print("\nEvidence:")

    if evidence:
        for e in evidence:
            print("-", e["sentence"])
    else:
        print("- No strong evidence found")


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":

    user_query = "What is Naruto’s birthday?"
    run_pipeline(query=user_query, domain="anime")