"""
Seed script — builds the knowledge base from scratch.

Run this once after cloning the project (or whenever you add new source files):

    python seed_documents.py

What it does:
1. Reads every .txt document in the ./data folder.
2. Chunks and embeds each one into ChromaDB (the vector store used for retrieval).
3. Registers a matching, admin-approved Document record in the database.

This makes the project fully portable: a fresh clone can regenerate the entire
vector store with a single command — no pre-built data needs to be committed.
"""

import asyncio
import os
from datetime import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal, Base, engine
from app.models.document import Document
from app.services.ingestion_service import IngestionService
from app.services.rag_service import RAGService


DATA_DIR = "./data"


# Ensures the database tables exist before we insert Document records.
async def _ensure_tables():
    from app.models import User, Conversation, Message, Document, Feedback  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Counts how many chunks for this filename already exist in ChromaDB.
def _existing_chunk_count(rag: RAGService, filename: str) -> int:
    try:
        result = rag.vector_store.get(where={"source": filename}, include=[])
        return len(result.get("ids", []))
    except Exception:
        return 0


async def seed():
    if not os.path.isdir(DATA_DIR):
        print(f"ERROR: '{DATA_DIR}' folder not found.")
        return

    files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".txt")]

    if not files:
        print(f"No .txt documents found in '{DATA_DIR}'.")
        return

    print("=" * 60)
    print(f"Seeding knowledge base from {len(files)} document(s) in '{DATA_DIR}'")
    print("=" * 60)

    await _ensure_tables()

    ingestion = IngestionService()
    rag = ingestion.rag_service

    indexed = 0

    async with AsyncSessionLocal() as session:
        for filename in files:
            file_path = os.path.join(DATA_DIR, filename)

            # Skip if this document is already indexed in ChromaDB.
            if _existing_chunk_count(rag, filename) > 0:
                print(f"  - {filename}: already indexed, skipping")
                continue

            print(f"  - {filename}: indexing...")
            result = await ingestion.process_text_file(file_path, filename)

            if result["status"] != "completed":
                print(f"      FAILED: {result.get('error')}")
                continue

            chunk_count = result["chunk_count"]
            print(f"      indexed {chunk_count} chunks")

            # Register (or update) the Document record so it appears as a
            # trusted, approved source in the Knowledge view.
            existing = await session.execute(
                select(Document).where(Document.filename == filename)
            )
            doc = existing.scalar_one_or_none()

            if doc is None:
                doc = Document(
                    filename=filename,
                    file_type="txt",
                    file_size=os.path.getsize(file_path),
                    description="Seeded trusted health guideline",
                    status="completed",
                    chunk_count=chunk_count,
                    source_trusted=True,
                    publisher="World Health Organization",
                    admin_approved=True,
                    approved_by="seed",
                    approved_at=datetime.utcnow(),
                    processed_at=datetime.utcnow(),
                    validation_notes="Seeded from ./data — trusted source",
                )
                session.add(doc)
            else:
                doc.status = "completed"
                doc.chunk_count = chunk_count
                doc.source_trusted = True
                doc.admin_approved = True

            indexed += 1

        await session.commit()

    print("=" * 60)
    print(f"Done. {indexed} document(s) newly indexed into ChromaDB.")
    print("=" * 60)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
