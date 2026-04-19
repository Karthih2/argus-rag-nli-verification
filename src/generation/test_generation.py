# src/generation/test_generation.py

import json
from src.generation.prompt_template import build_argus_prompt
from src.generation.llm import generate_answer


# Chunk format
chunks = [
    {
        "text": "Basic training typically spans two years, covering spacewalk procedures, vehicle systems, and Russian language.",
        "file_name": "astronaut_training.pdf",
        "source": {"page": 5}
    },
    {
        "text": "Astronaut candidates undergo physical and academic preparation before being assigned missions.",
        "file_name": "astronaut_training.pdf",
        "source": {"page": 3}
    }
]


query = "How long is astronaut training?"


def run_test():
    try:
        print("Building prompt...\n")

        prompt = build_argus_prompt(query, chunks)

        print("Generating answer...\n")

        answer_json = generate_answer(prompt)

        print("Final Structured Output:\n")
        print(json.dumps(answer_json, indent=4))

    except Exception as e:
        print("Error during generation:")
        print(str(e))


if __name__ == "__main__":
    run_test()