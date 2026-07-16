# src/main.py

import json
import time
from pathlib import Path

from src.generation.prompt_template import build_argus_prompt
from src.generation.llm import generate_answer
from src.verification.hallucination_checker import HallucinationChecker
from src.reasoning.evidence_extractor import extract_evidence
from src.evaluation.simple_eval import run_simple_evaluation
from src.retrieval.retriever import Retriever


# CONFIG
LOG_DIR = Path("logs")
MAX_RETRIES = 2

retriever_cache = {}


# RETRIEVER CACHE
def get_retriever(domain: str):
    """
    Load retriever only once per domain
    """
    if domain not in retriever_cache:
        retriever_cache[domain] = Retriever(domain=domain)

    return retriever_cache[domain]


# RETRIEVE DOCUMENT CHUNKS
def retrieve_chunks(
    query: str,
    domain: str = "nasa",
    top_k: int = 8
) -> list:

    retriever = get_retriever(domain)

    results = retriever.retrieve(
        query=query,
        top_k=top_k
    )

    chunks = []

    for doc in results:
        chunks.append(
            {
                "text": doc.get("text", ""),
                "file_name": doc.get("file_name", "unknown.pdf"),
                "source": {
                    "page": doc.get("source", {}).get("page", "N/A")
                }
            }
        )

    print(f"\nRetrieved chunks: {len(chunks)}")

    return chunks


# SAVE LOGS
def save_log(data: dict) -> None:

    LOG_DIR.mkdir(exist_ok=True)

    file_path = LOG_DIR / f"log_{int(time.time())}.json"

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


# TRUST SCORE
def calculate_trust_score(
    label: str,
    confidence: float
) -> int:

    if label == "entailment":
        return min(100, round(confidence * 100))

    if label == "weak_support":
        return round(confidence * 75)

    if label == "neutral":
        return round(confidence * 50)

    if label == "contradiction":
        return 0

    if label == "no_support":
        return 0

    return 0


# GENERATE + VERIFY ANSWER
def generate_verified_answer(
    query: str,
    chunks: list,
    checker
):

    final_answer = None
    final_label = "unknown"
    final_confidence = 0.0
    final_debug = {}

    for attempt in range(MAX_RETRIES + 1):

        try:
            prompt = build_argus_prompt(query, chunks)

            answer_json = generate_answer(prompt)

            label, confidence, debug = checker.verify(
                answer_json,
                chunks
            )

            final_answer = answer_json
            final_label = label
            final_confidence = confidence
            final_debug = debug

            if label == "entailment" and confidence >= 0.85:
                break

            if attempt < MAX_RETRIES:
                print(f"Retrying generation... ({attempt + 1})")

        except Exception as e:
            print("Generation Error:", str(e))

            final_answer = {
                "answer": "Unable to generate verified answer.",
                "evidence": []
            }

            final_label = "no_support"
            final_confidence = 0.0
            final_debug = {}

    return (
        final_answer,
        final_label,
        final_confidence,
        final_debug
    )


# MAIN PIPELINE
def run_pipeline(
    query: str,
    domain: str = "nasa"
) -> dict:

    start_time = time.time()

    checker = HallucinationChecker()

    # STEP 1: RETRIEVE
    chunks = retrieve_chunks(
        query=query,
        domain=domain,
        top_k=8
    )

    if not chunks:
        return {
            "query": query,
            "domain": domain,
            "answer": "No relevant documents found.",
            "verdict": "no_support",
            "confidence": 0.0,
            "trust_score": 0,
            "latency": 0,
            "evidence": []
        }

    # STEP 2: GENERATE + VERIFY
    answer_json, label, confidence, debug = generate_verified_answer(
        query=query,
        chunks=chunks,
        checker=checker
    )

    # SAFE RESPONSE FORMAT
    if not isinstance(answer_json, dict):
        answer_json = {
            "answer": str(answer_json),
            "evidence": []
        }

    answer_text = answer_json.get("answer", "")

    # STEP 3: EVIDENCE EXTRACTION
    evidence = extract_evidence(
        chunks,
        answer_text
    )

    # STEP 4: METRICS
    latency = round(time.time() - start_time, 2)

    trust_score = calculate_trust_score(
        label,
        confidence
    )

    # STEP 5: LOGGING
    save_log(
        {
            "query": query,
            "domain": domain,
            "retrieved_docs": len(chunks),
            "latency_sec": latency,
            "verdict": label,
            "confidence": round(confidence, 4),
            "trust_score": trust_score
        }
    )

    # STEP 6: TERMINAL OUTPUT
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

    print("\nEvidence:")

    if evidence:
        for item in evidence:
            print("-", item.get("sentence", item))
    else:
        print("- No strong evidence found")

    # STEP 7: SIMPLE EVAL
    try:
        run_simple_evaluation(
            query=query,
            answer=answer_text,
            chunks=chunks,
            label=label,
            confidence=confidence
        )

    except Exception as e:
        print("Evaluation Error:", str(e))

    # RETURN FOR STREAMLIT / API
    return {
        "query": query,
        "domain": domain,
        "answer": answer_text,
        "verdict": label,
        "confidence": round(confidence, 4),
        "trust_score": trust_score,
        "latency": latency,
        "evidence": evidence
    }


# ENTRY POINT
if __name__ == "__main__":
    print("Run using Streamlit frontend:")
    print("streamlit run app.py")