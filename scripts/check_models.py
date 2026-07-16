# check_models.py

import os
from groq import Groq
from dotenv import load_dotenv

# Load API key
load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Fetch models
models = client.models.list()

print("\n✅ AVAILABLE MODELS:\n")

for m in models.data:
    print(f"- {m.id}")