"""
Document Routes
===============
Handles document ingestion, validation, approval, source retrieval,
document listing, and viewing of verified source files.
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.document import Document
from app.services.document_validation_service import DocumentValidationService
from app.services.ingestion_service import IngestionService


router = APIRouter(tags=["Documents"])


# ============================================================
# DOCUMENT UPLOAD
# ============================================================

@router.post("/ingest")
async def ingest_document(
    file: UploadFile = File(..., description="Medical PDF to upload"),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    file_size = len(content)

    validator = DocumentValidationService()

    validation = validator.validate_document(
        filename=file.filename or "unnamed.pdf",
        content_type=file.content_type or "",
        file_content=content,
    )

    if not validation["valid"]:
        raise HTTPException(
            status_code=400,
            detail=validation.get("error", "Validation failed"),
        )

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

    upload_dir = "./uploads"
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(
        upload_dir,
        f"{doc.id}.pdf",
    )

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


# ============================================================
# ADMIN APPROVAL
# ============================================================

@router.post("/ingest/approve/{document_id}")
async def approve_document(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )

    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    if doc.status != "pending_approval":
        raise HTTPException(
            status_code=400,
            detail=f"Document is '{doc.status}', not 'pending_approval'",
        )

    doc.admin_approved = True
    doc.approved_by = "admin"
    doc.approved_at = datetime.utcnow()
    doc.status = "processing"

    await db.flush()

    file_path = f"./uploads/{doc.id}.pdf"

    if not os.path.exists(file_path):
        doc.status = "failed"
        doc.validation_notes = "Upload file not found on disk"

        return {
            "error": "File not found for processing"
        }

    try:
        ingestion = IngestionService()

        process_result = await ingestion.process_pdf(
            file_path,
            doc.filename,
        )

        doc.status = process_result["status"]
        doc.chunk_count = process_result.get("chunk_count", 0)

        if process_result["status"] == "completed":
            doc.processed_at = datetime.utcnow()

    except Exception as e:
        doc.status = "failed"
        doc.validation_notes = f"Processing error: {str(e)}"

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


# ============================================================
# SOURCE METADATA
# ============================================================

@router.get("/sources/{document_id}")
async def get_source(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )

    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Source document not found",
        )

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


# ============================================================
# LIST VERIFIED DOCUMENTS
# ============================================================

@router.get("/documents")
async def list_documents(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc())
    )

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
                "created_at": (
                    d.created_at.isoformat()
                    if d.created_at
                    else None
                ),
            }
            for d in documents
        ],
    }


# ============================================================
# VIEW ORIGINAL VERIFIED DOCUMENT
# ============================================================

@router.get("/documents/{document_id}/file")
async def get_document_file(
    document_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the original verified document.

    PDFs are opened directly in the browser.
    TXT documents are returned as readable text.
    """

    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )

    doc = result.scalar_one_or_none()

    if not doc:
        raise HTTPException(
            status_code=404,
            detail="Document not found",
        )

    # Users can only view trusted, approved and indexed documents.
    if (
        not doc.source_trusted
        or not doc.admin_approved
        or doc.status != "completed"
    ):
        raise HTTPException(
            status_code=403,
            detail="This document is not available to users.",
        )

    filename = doc.filename

    # --------------------------------------------------------
    # Look for the original document.
    #
    # Seeded documents:
    #     ./sample_docs/<filename>
    #
    # Uploaded documents:
    #     ./uploads/<document_id>.pdf
    # --------------------------------------------------------

    sample_path = os.path.join(
        "./sample_docs",
        filename,
    )

    upload_path = os.path.join(
        "./uploads",
        f"{document_id}.pdf",
    )

    if os.path.exists(sample_path):
        file_path = sample_path

    elif os.path.exists(upload_path):
        file_path = upload_path

    else:
        raise HTTPException(
            status_code=404,
            detail=(
                f"Original document '{filename}' "
                "could not be found on the server."
            ),
        )

    # --------------------------------------------------------
    # PDF
    # --------------------------------------------------------

    if filename.lower().endswith(".pdf"):
        return FileResponse(
            path=file_path,
            media_type="application/pdf",
            filename=filename,
            content_disposition_type="inline",
        )

    # --------------------------------------------------------
    # TXT
    # --------------------------------------------------------

    if filename.lower().endswith(".txt"):
        try:
            with open(
                file_path,
                "r",
                encoding="utf-8",
            ) as f:
                content = f.read()

            return PlainTextResponse(
                content=content,
                media_type="text/plain",
            )

        except UnicodeDecodeError:
            raise HTTPException(
                status_code=500,
                detail="Unable to read the document text.",
            )

    raise HTTPException(
        status_code=400,
        detail="Unsupported document format.",
    )