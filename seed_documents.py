

import asyncio
import os
from app.services.ingestion_service import IngestionService


SAMPLE_DOCS_DIR = "./sample_docs"


async def seed():
    
    ingestion = IngestionService()

    if not os.path.exists(SAMPLE_DOCS_DIR):
        print(f"ERROR: {SAMPLE_DOCS_DIR} directory not found")
        return

    files = [f for f in os.listdir(SAMPLE_DOCS_DIR) if f.endswith((".txt", ".pdf"))]

    if not files:
        print(f"No documents found in {SAMPLE_DOCS_DIR}/")
        return

    print(f"Found {len(files)} documents to ingest...")
    print("=" * 50)

    total_chunks = 0

    for filename in files:
        filepath = os.path.join(SAMPLE_DOCS_DIR, filename)
        print(f"\nProcessing: {filename}")

        if filename.endswith(".txt"):
            result = await ingestion.process_text_file(filepath, filename)
        elif filename.endswith(".pdf"):
            result = await ingestion.process_pdf(filepath, filename)
        else:
            continue

        if result["status"] == "completed":
            print(f"  ✅ Success — {result['chunk_count']} chunks stored in ChromaDB")
            total_chunks += result["chunk_count"]
        else:
            print(f"  ❌ Failed — {result.get('error', 'Unknown error')}")

    print("\n" + "=" * 50)
    print(f"DONE: {total_chunks} total chunks stored in ChromaDB")
    print("The chatbot can now answer questions about these documents.")


if __name__ == "__main__":
    asyncio.run(seed())
