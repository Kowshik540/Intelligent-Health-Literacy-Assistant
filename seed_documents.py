import asyncio
import os

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.document import Document
from app.services.document_validation_service import DocumentValidationService
from app.services.rag_service import RAGService


SAMPLE_DOCS_DIR = "./sample_docs"


async def get_chroma_chunk_count(rag_service: RAGService, filename: str) -> int:
    """Return the number of existing ChromaDB chunks for this document."""
    try:
        result = rag_service.vector_store.get(
            where={"source": filename},
            include=[],
        )

        return len(result.get("ids", []))

    except Exception as e:
        print(f"  ⚠ Could not read ChromaDB: {e}")
        return 0


async def seed():
    """
    Register already-indexed knowledge documents in PostgreSQL.

    IMPORTANT:
    This does NOT re-index the PDFs.
    It only creates the missing Document records.
    """

    if not os.path.exists(SAMPLE_DOCS_DIR):
        print(f"ERROR: {SAMPLE_DOCS_DIR} directory not found")
        return

    files = [
        f
        for f in os.listdir(SAMPLE_DOCS_DIR)
        if f.lower().endswith((".pdf", ".txt"))
    ]

    if not files:
        print(f"No documents found in {SAMPLE_DOCS_DIR}/")
        return

    print(f"Found {len(files)} documents")
    print("=" * 60)

    validator = DocumentValidationService()
    rag_service = RAGService()

    created = 0
    skipped = 0

    async with AsyncSessionLocal() as db:

        for filename in sorted(files):

            print(f"\nChecking: {filename}")

            # Check whether PostgreSQL already has this document
            result = await db.execute(
                select(Document).where(Document.filename == filename)
            )

            existing = result.scalar_one_or_none()

            if existing:
                print(
                    f"  ✓ Already registered "
                    f"(status={existing.status}, chunks={existing.chunk_count})"
                )
                skipped += 1
                continue

            filepath = os.path.join(SAMPLE_DOCS_DIR, filename)

            try:
                with open(filepath, "rb") as f:
                    content = f.read()
            except Exception as e:
                print(f"  ❌ Could not read file: {e}")
                continue

            # Validate PDF
            if filename.lower().endswith(".pdf"):
                validation = validator.validate_document(
                    filename=filename,
                    content_type="application/pdf",
                    file_content=content,
                )
            else:
                validation = {
                    "valid": True,
                    "file_hash": None,
                    "publisher": "WHO / Verified Medical Reference",
                    "isbn_reference": None,
                    "source_trusted": True,
                    "validation_notes": "Verified knowledge document",
                }

            if not validation["valid"]:
                print(
                    f"  ❌ Validation failed: "
                    f"{validation.get('error', 'Unknown error')}"
                )
                continue

            # IMPORTANT:
            # Read existing chunks from ChromaDB.
            # We are NOT adding them again.
            chunk_count = await get_chroma_chunk_count(
                rag_service,
                filename,
            )

            if chunk_count == 0:
                print("  ⚠ No ChromaDB chunks found — skipped")
                continue

            # Create PostgreSQL record
            document = Document(
                filename=filename,
                file_type="pdf",
                file_size=len(content),
                status="completed",
                description="Verified medical knowledge source",
                file_hash=validation.get("file_hash"),
                publisher=validation.get("publisher"),
                isbn_reference=validation.get("isbn_reference"),
                source_trusted=validation.get("source_trusted", True),
                validation_notes=validation.get("validation_notes"),
                admin_approved=True,
                approved_by="system",
                chunk_count=chunk_count,
            )

            db.add(document)
            await db.flush()

            print("  ✅ Registered in PostgreSQL")
            print(f"     ChromaDB chunks: {chunk_count}")
            print(f"     Trusted: {document.source_trusted}")
            print(f"     Status: {document.status}")

            created += 1

        await db.commit()

    print("\n" + "=" * 60)
    print("DATABASE REGISTRATION COMPLETE")
    print(f"New documents registered: {created}")
    print(f"Already registered:       {skipped}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())