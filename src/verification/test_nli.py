# src/verfication/test_nli.py

from src.verification.hallucination_checker import HallucinationChecker
from src.verification.decision_gate import decide_action


def run_test():
    checker = HallucinationChecker()

    chunks = [
        {
            "text": "Basic training typically spans two years, covering spacewalk procedures, vehicle systems, and Russian language."
        },
        {
            "text": "Astronaut candidates undergo physical and academic preparation before being assigned missions."
        }
    ]

    tests = [
        {
            "name": "CORRECT ANSWER",
            "answer_json": {
                "answer": "Basic training typically spans two years."
            }
        },
        {
            "name": "WRONG ANSWER",
            "answer_json": {
                "answer": "Astronaut training lasts ten years."
            }
        }
    ]

    for test in tests:
        print("\n" + "=" * 60)
        print(test["name"])
        print("=" * 60)

        label, confidence, debug = checker.verify(
            test["answer_json"],
            chunks
        )

        action = decide_action(label, confidence)

        print("Answer     :", test["answer_json"]["answer"])
        print("Label      :", label)
        print("Confidence :", round(confidence, 4))
        print("Action     :", action)
        print("Debug      :", debug)


if __name__ == "__main__":
    run_test()