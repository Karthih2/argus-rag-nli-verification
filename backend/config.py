"""Settings and fallback values, read from .env at the repo root."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT_DIR / ".env", extra="ignore")

    # Database
    MONGO_URI: str = ""
    DB_NAME: str = "argus"

    # Groq
    GROQ_API_KEY: str = ""
    GROQ_MODELS: str = "openai/gpt-oss-120b,openai/gpt-oss-20b"

    # Hugging Face models
    HF_HOME: str = str(ROOT_DIR / "models" / "hf")
    EMBEDDING_MODEL: str = "BAAI/bge-base-en-v1.5"
    RERANKER_MODEL: str = "BAAI/bge-reranker-base"
    NLI_MODEL_NAME: str = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"
    NLI_MAX_PREMISE_TOKENS: int = 400
    NLI_BATCH_SIZE: int = 16

    # Chunking and retrieval
    CHUNK_MAX_TOKENS: int = 400  # matches NLI_MAX_PREMISE_TOKENS — no chunk truncated at NLI time
    TABLE_ROWS_PER_CHUNK: int = 5
    TABLE_MAX_ROWS_WHOLE: int = 15
    RETRIEVE_LIMIT: int = 30
    NUM_CANDIDATES: int = 400
    RRF_K: int = 60
    RERANK_KEEP: int = 8
    CONTEXT_MAX_TOKENS: int = 3500
    INDEX_READY_TIMEOUT_S: int = 90

    # Upload limits
    MAX_UPLOAD_MB: int = 50
    MAX_PAGES: int = 500
    MAX_FILES_PER_UPLOAD: int = 5

    # Quote check
    QUOTE_MIN_CHARS: int = 15

    # Trust score policy (only human-set numbers)
    RISK_VERIFIED: float = 0.05
    RISK_WITHHOLD: float = 0.02

    # API
    CORS_ORIGINS: str = "http://localhost:5173"
    RATE_LIMIT_PER_MINUTE: int = 20

    @property
    def groq_model_list(self) -> list[str]:
        """Main model first, then fallbacks."""
        return [m.strip() for m in self.GROQ_MODELS.split(",") if m.strip()]


settings = Settings()
