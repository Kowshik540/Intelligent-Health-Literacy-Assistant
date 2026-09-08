"""
Application Configuration
==========================
Centralizes all environment variables and application settings using Pydantic.
Values are loaded from the .env file at project root.

This follows the 12-Factor App methodology — all config comes from environment,
making the application portable across dev/staging/production environments.
"""

import os

# Silence ChromaDB's anonymized telemetry. In chromadb 0.5.x the telemetry
# client raises noisy "capture() takes 1 positional argument" errors and can
# cause a non-zero process exit code, which is confusing during testing. This
# has no effect on functionality. Set before chromadb is imported anywhere.
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")

# chromadb 0.5.x still tries to emit a few lifecycle telemetry events even when
# telemetry is disabled, and its posthog client logs a harmless
# "capture() takes 1 positional argument but 3 were given" error each time.
# Silence that specific logger so testers don't see confusing (but harmless)
# error lines. This does not affect functionality.
import logging

logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # --- Application ---
    APP_NAME: str = "Healthcare Intelligent Health Literacy Assistant"
    DEBUG: bool = True
    API_VERSION: str = "v1"

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # --- Database ---
    # Defaults to SQLite so the app runs with ZERO setup (no DB server needed).
    # To use PostgreSQL, set DATABASE_URL in .env, e.g.:
    #   postgresql://user:password@localhost:5432/healthcare_db
    DATABASE_URL: str = "sqlite:///./healthcare.db"

    # --- LLM Configuration ---
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"

    # --- Ollama (Local LLM — no data leaves the server) ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2:1.5b"
    USE_OLLAMA: bool = True

    # --- Vector Database (ChromaDB) ---
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_data"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # --- Observability (LangSmith) ---
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "healthcare-assistant"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
