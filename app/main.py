"""
Application Entry Point
========================
FastAPI application factory with lifespan management.
Handles startup (database init, model pre-loading) and shutdown (cleanup).

Run: uvicorn app.main:app --host 0.0.0.0 --port 8003
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

    # Create all tables (idempotent — skips if they exist)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default user for demo/development
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

    # Pre-load embedding model so first request is fast (~20s saved)
    from app.services.chat_service import _get_rag_service
    _get_rag_service()

    print(f"Starting {settings.APP_NAME}...")
    print(f"LLM: {settings.OLLAMA_MODEL} (Ollama)" if settings.USE_OLLAMA else f"LLM: {settings.OPENAI_MODEL}")
    print(f"Database: {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")

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

# CORS — allows frontend (React) to communicate with backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
