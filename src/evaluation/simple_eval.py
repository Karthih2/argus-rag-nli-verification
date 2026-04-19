# src/evaluation/simple_eval.py

def run_simple_evaluation(query, answer, chunks, label, confidence):

    print("\nARGUS EVALUATION")

    retrieval_score = min(1.0, len(chunks) / 5)
    faithfulness = confidence
    hallucination_risk = 1 - confidence if label != "entailment" else 0

    print("Retrieval Score   :", round(retrieval_score, 3))
    print("Faithfulness      :", round(faithfulness, 3))
    print("Hallucination Risk:", round(hallucination_risk, 3))

    return {
        "retrieval_score": retrieval_score,
        "faithfulness": faithfulness,
        "hallucination_risk": hallucination_risk
    }