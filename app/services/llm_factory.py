"""
LLM & Embedding Factory
=======================
Central place that builds the chat model and the embedding model used across
the app (RAG service, jargon simplifier, graph agent).

Why this exists
---------------
LangChain has been splitting integrations out of ``langchain_community`` into
standalone packages (``langchain_ollama``, ``langchain_huggingface``,
``langchain_chroma``). Depending on the exact installed versions, the classes
live in different places. Centralising the imports here means:

* every service builds its LLM the same way (consistent temperature handling,
  consistent Ollama vs OpenAI selection);
* the app keeps working whether the modern standalone packages or the older
  ``langchain_community`` ones are installed.

All builders return ``None`` gracefully when no provider is configured, so the
callers can degrade cleanly instead of crashing at import time.
"""

from __future__ import annotations

from typing import Optional

from app.core.config import settings


# --------------------------------------------------------------------------- #
# Chat model
# --------------------------------------------------------------------------- #
def build_chat_llm(temperature: float = 0.1, num_predict: Optional[int] = None):
    """
    Build the chat LLM based on configuration.

    Priority:
      1. Ollama (local) when ``USE_OLLAMA`` is true.
      2. OpenAI when an API key is set.
      3. ``None`` when nothing is configured (callers degrade gracefully).
    """
    if settings.USE_OLLAMA:
        ChatOllama = _import_chat_ollama()
        kwargs = {
            "model": settings.OLLAMA_MODEL,
            "base_url": settings.OLLAMA_BASE_URL,
            "temperature": temperature,
        }
        if num_predict is not None:
            kwargs["num_predict"] = num_predict
        return ChatOllama(**kwargs)

    if settings.OPENAI_API_KEY:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,
        )

    return None


def _import_chat_ollama():
    """Return the ChatOllama class from whichever package provides it."""
    # Preferred: standalone package (actively maintained).
    try:
        from langchain_ollama import ChatOllama  # type: ignore

        return ChatOllama
    except ImportError:
        pass

    # Fallback: older langchain_community location.
    from langchain_community.chat_models import ChatOllama  # type: ignore

    return ChatOllama


# --------------------------------------------------------------------------- #
# Embeddings
# --------------------------------------------------------------------------- #
def build_embeddings():
    """
    Build the HuggingFace sentence-transformer embeddings (CPU, normalised).

    Tries the standalone ``langchain_huggingface`` package first, then falls
    back to ``langchain_community``.
    """
    try:
        from langchain_huggingface import HuggingFaceEmbeddings  # type: ignore
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore

    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


# --------------------------------------------------------------------------- #
# Vector store
# --------------------------------------------------------------------------- #
def build_chroma(embeddings, collection_name: str = "medical_documents"):
    """
    Build the Chroma vector store, persisted to ``CHROMA_PERSIST_DIRECTORY``.

    Tries the standalone ``langchain_chroma`` package first, then falls back to
    ``langchain_community``.
    """
    try:
        from langchain_chroma import Chroma  # type: ignore
    except ImportError:
        from langchain_community.vectorstores import Chroma  # type: ignore

    return Chroma(
        persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
        embedding_function=embeddings,
        collection_name=collection_name,
    )
