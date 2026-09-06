"""
Application Entry Point
========================
FastAPI application factory with lifespan management.
Handles startup (database init, model pre-loading) and shutdown (cleanup).

Run: uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine
from app.api.v1.router import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    - Creates database tables if they don't exist
    - Seeds the default demo user
    - Pre-loads the embedding model for fast first-request response
    - Configures LangSmith observability if enabled
    """
    # Configure LangSmith tracing
    if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
        os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT

    from app.core.database import Base, AsyncSessionLocal
    from app.models import User, Conversation, Message, Document, Feedback

    # Create tables and seed the demo user. Wrapped so a transient database
    # issue is reported clearly instead of silently crashing the whole app.
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.id == "default-user-001")
            )
            if not result.scalar_one_or_none():
                default_user = User(
                    id="default-user-001",
                    username="demo_user",
                    email="demo@healthassistant.local",
                )
                session.add(default_user)
                await session.commit()
    except Exception as e:
        print(f"[WARNING] Database initialization failed: {e}")
        print("          Check DATABASE_URL in your .env (SQLite works with no setup).")

    # Pre-load embedding model so the first request is fast. Non-fatal if it
    # fails — the model will simply load on the first request instead.
    try:
        from app.services.chat_service import _get_rag_service
        _get_rag_service()
    except Exception as e:
        print(f"[WARNING] Could not pre-load the embedding model: {e}")

    # Clear startup banner so testers immediately know how it is configured.
    db_label = (
        settings.DATABASE_URL.split("@")[-1]
        if "@" in settings.DATABASE_URL
        else settings.DATABASE_URL
    )
    print("=" * 60)
    print(f"  {settings.APP_NAME}")
    print(f"  API:      http://localhost:{settings.PORT}")
    print(f"  Docs:     http://localhost:{settings.PORT}/docs")
    if settings.USE_OLLAMA:
        print(f"  LLM:      Ollama '{settings.OLLAMA_MODEL}' at {settings.OLLAMA_BASE_URL}")
        print(f"            (run: ollama pull {settings.OLLAMA_MODEL})")
    elif settings.OPENAI_API_KEY:
        print(f"  LLM:      OpenAI '{settings.OPENAI_MODEL}'")
    else:
        print("  LLM:      NONE configured — set USE_OLLAMA or OPENAI_API_KEY")
    print(f"  Database: {db_label}")
    print("=" * 60)

    yield

    # Cleanup
    await engine.dispose()


# --- Application Factory ---

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
    description="RAG-based health literacy assistant using verified WHO medical documents",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS — allows the frontend (any host/port) to talk to the backend.
# allow_credentials is False because we don't use cookies; this makes the
# wildcard origin valid (browsers reject "*" combined with credentials).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes
app.include_router(api_v1_router)


@app.get("/")
async def root():
    """Root endpoint — confirms the service is running."""
    return {
        "message": settings.APP_NAME,
        "status": "running",
        "version": settings.API_VERSION,
    }
