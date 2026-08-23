"""
Document Repository
====================
Handles all database operations for medical document records.
Manages the document lifecycle: upload → validation → approval → indexing.
"""

from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document


class DocumentRepository:
    """Repository for Document persistence and lifecycle management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Document:
        """Create a new document record."""
        doc = Document(**kwargs)
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def get_by_id(self, doc_id: str) -> Optional[Document]:
        """Fetch a document by its ID."""
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()

    async def get_all(self) -> list[Document]:
        """Get all documents ordered by creation date (newest first)."""
        result = await self.db.execute(
            select(Document).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self, doc_id: str, status: str, chunk_count: int = 0
    ) -> Optional[Document]:
        """Update document processing status."""
        doc = await self.get_by_id(doc_id)
        if doc:
            doc.status = status
            doc.chunk_count = chunk_count
            if status == "completed":
                doc.processed_at = datetime.utcnow()
        return doc

    async def approve(self, doc_id: str, approved_by: str = "admin") -> Optional[Document]:
        """Mark a document as admin-approved for ChromaDB indexing."""
        doc = await self.get_by_id(doc_id)
        if doc:
            doc.admin_approved = True
            doc.approved_by = approved_by
            doc.approved_at = datetime.utcnow()
            doc.status = "processing"
        return doc
