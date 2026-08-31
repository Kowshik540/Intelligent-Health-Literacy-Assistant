"""
Document Seeding Script (Phase 1)
===================================
Ingests all WHO medical PDFs from sample_docs/ into ChromaDB.
Run this once after setting up the environment to populate the vector store.

Run: python seed_documents.py
"""

import asyncio
import os
import sys
sys.path.insert(0, ".")

from app.services.ingestion_service import IngestionService

SAMPLE_DOCS_DIR = "./sample_docs"


async def seed():
    ingestion = IngestionService()

    if not os.path.exists(SAMPLE_DOCS_DIR):
        print(f"ERROR: {SAMPLE_DOCS_DIR}/ not found")
        return

    files = [f for f in os.listdir(SAMPLE_DOCS_DIR) if f.endswith((".txt", ".pdf"))]
    print(f"Found {len(files)} documents to ingest...")
    print("=" * 50)

    total_chunks = 0
    for filename in files:
        filepath = os.path.join(SAMPLE_DOCS_DIR, filename)
        print(f"Processing: {filename}")

        if filename.endswith(".txt"):
            result = await ingestion.process_text_file(filepath, filename)
        else:
            result = await ingestion.process_pdf(filepath, filename)

        if result["status"] == "completed":
            print(f"  {result['chunk_count']} chunks stored")
            total_chunks += result["chunk_count"]
        else:
            print(f"  Failed: {result.get('error')}")

    print("=" * 50)
    print(f"Done. {total_chunks} total chunks in ChromaDB.")


if __name__ == "__main__":
    asyncio.run(seed())
