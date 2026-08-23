
# Run: uvicorn app.main:app --reload --port 8000


from fastapi import FastAPI
from app.core.config import settings
from app.core.database import engine, Base

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.API_VERSION,
)


@app.on_event("startup")
async def startup():
    """Initialize database tables on startup."""
    from app.models.document import Document  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print(f"Starting {settings.APP_NAME}...")
    print(f"LLM: {settings.OLLAMA_MODEL} (Ollama)")


@app.on_event("shutdown")
async def shutdown():
    await engine.dispose()


# --- Phase 1 Endpoints ---

# Health check — verifies service is running
@app.get("/api/v1/health")
async def health_check():
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.API_VERSION,
    }


# --- Phase 2 Endpoints (In Progress) ---

# Chat endpoint — runs query through guardrails + RAG pipeline
@app.post("/api/v1/chat")
async def chat(request: dict):
    from app.services.guardrails_service import GuardrailsService
    from app.services.rag_service import RAGService

    message = request.get("message", "")

    # Step 1: Safety check (emergency detection + PII removal)
    guardrails = GuardrailsService()
    check = guardrails.check_query(message)

    if not check.is_safe:
        return {
            "answer": check.refusal_message,
            "is_emergency": True,
            "pii_detected": False,
            "citations": [],
        }

    # Step 2: RAG retrieval + LLM answer generation
    rag = RAGService()
    response = await rag.get_response(check.sanitized_query)

    return {
        "answer": response["answer"],
        "sources": response["sources"],
        "citations": response["citations"],
        "is_emergency": False,
        "pii_detected": check.pii_detected,
    }


# TODO (Phase 2): Jargon simplifier endpoint
# TODO (Phase 3): Document upload/approval endpoints
# TODO (Phase 3): Feedback endpoints

@app.get("/")
async def root():
    return {"message": settings.APP_NAME, "status": "Phase 1 complete, Phase 2 in progress"}
