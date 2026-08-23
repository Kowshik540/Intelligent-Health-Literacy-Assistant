"""
Document Routes — Handles PDF upload, validation, admin approval, and source retrieval.
"""

import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from app.core.database import get_db
from app.models.document import Document
from app.services.document_validation_service import DocumentValidationService
from app.services.document_service import DocumentService
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["Documents"])


# Uploads a medical PDF, runs it through the validation pipeline, and stores it pending admin approval
@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(..., description="Medical PDF to upload"),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    file_size = len(content)

    # Run the document through the validation pipeline (file type, hash, source check)
    validator = DocumentValidationService()
    validation = validator.validate_document(
        filename=file.filename or "unnamed.pdf",
        content_type=file.content_type or "",
        file_content=content,
    )

    if not validation["valid"]:
        raise HTTPException(status_code=400, detail=validation.get("error", "Validation failed"))

    # Create document record in pending_approval status
    doc = Document(
        filename=file.filename or "unnamed.pdf",
        file_type="pdf",
        file_size=file_size,
        description=description,
        status="pending_approval",
        file_hash=validation.get("file_hash"),
        publisher=validation.get("publisher"),
        isbn_reference=validation.get("isbn_reference"),
        source_trusted=validation.get("source_trusted", False),
        validation_notes=validation.get("validation_notes"),
    )
    db.add(doc)
    await db.flush()

    # Save file to disk for later processing after approval
    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"{doc.id}.pdf")
    with open(file_path, "wb") as f:
        f.write(content)

    return {
        "message": "Document uploaded and validated. Awaiting admin approval.",
        "document_id": doc.id,
        "filename": doc.filename,
        "status": doc.status,
        "file_hash": doc.file_hash,
        "publisher": doc.publisher,
        "isbn_reference": doc.isbn_reference,
        "source_trusted": doc.source_trusted,
        "validation_notes": doc.validation_notes,
    }


# Admin approves a validated document — triggers chunking and ChromaDB indexing
@router.post("/ingest/approve/{document_id}")
async def approve_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Document is '{doc.status}', not 'pending_approval'"
        )

    # Mark as approved and begin processing
    doc.admin_approved = True
    doc.approved_by = "admin"
    doc.approved_at = datetime.utcnow()
    doc.status = "processing"
    await db.flush()

    # Process the PDF: extract text, chunk it, embed it, store in ChromaDB
    file_path = f"./uploads/{doc.id}.pdf"
    if not os.path.exists(file_path):
        doc.status = "failed"
        doc.validation_notes = "Upload file not found on disk"
        return {"error": "File not found for processing"}

    try:
        ingestion = IngestionService()
        process_result = await ingestion.process_pdf(file_path, doc.filename)

        doc.status = process_result["status"]
        doc.chunk_count = process_result.get("chunk_count", 0)
        if process_result["status"] == "completed":
            doc.processed_at = datetime.utcnow()

    except Exception as e:
        doc.status = "failed"
        doc.validation_notes = f"Processing error: {str(e)}"

    # Clean up the temp file after processing
    try:
        os.unlink(file_path)
    except Exception:
        pass

    return {
        "message": f"Document '{doc.filename}' approved and indexed in ChromaDB",
        "document_id": doc.id,
        "status": doc.status,
        "chunk_count": doc.chunk_count,
    }


# Retrieves metadata for a specific source document (used by the citation sidebar)
@router.get("/sources/{document_id}")
async def get_source(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(status_code=404, detail="Source document not found")

    return {
        "document_id": doc.id,
        "filename": doc.filename,
        "publisher": doc.publisher,
        "isbn_reference": doc.isbn_reference,
        "chunk_count": doc.chunk_count,
        "status": doc.status,
        "source_trusted": doc.source_trusted,
        "file_hash": doc.file_hash,
    }


# Lists all documents in the system with their validation/approval status
@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    documents = result.scalars().all()
    return {
        "total": len(documents),
        "documents": [
            {
                "id": d.id,
                "filename": d.filename,
                "status": d.status,
                "file_hash": d.file_hash,
                "publisher": d.publisher,
                "source_trusted": d.source_trusted,
                "admin_approved": d.admin_approved,
                "chunk_count": d.chunk_count,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in documents
        ],
    }
