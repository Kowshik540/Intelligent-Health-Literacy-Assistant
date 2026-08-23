"""
Application Configuration
==========================
Centralizes environment variables using Pydantic Settings.
Phase 1: Database + ChromaDB settings
Phase 2: Added Ollama LLM configuration
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Healthcare Intelligent Health Literacy Assistant"
    DEBUG: bool = True
    API_VERSION: str = "v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # PostgreSQL Database (Phase 1)
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/healthcare_db"

    # ChromaDB Vector Store (Phase 1)
    CHROMA_PERSIST_DIRECTORY: str = "./chroma_data"
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Ollama LLM — local inference, no data leaves server (Phase 2)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2:1.5b"
    USE_OLLAMA: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
