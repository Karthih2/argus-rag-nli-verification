# src/config/settings.py

import os
from dotenv import load_dotenv

load_dotenv()

# API KEYS
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# MODELS
MODEL_PRIORITY = [
    "qwen/qwen3-32b",
    "llama-3.3-70b-versatile",
    "meta-llama/llama-4-scout-17b-16e-instruct"
]

# GENERATION SETTINGS
TEMPERATURE = 0
MAX_TOKENS = 512

# RETRIEVAL SETTINGS
TOP_K = 3

# VERIFICATION SETTINGS
ENTAILMENT_THRESHOLD = 0.75
CONTRADICTION_THRESHOLD = 0.80
WEAK_SUPPORT_THRESHOLD = 0.85