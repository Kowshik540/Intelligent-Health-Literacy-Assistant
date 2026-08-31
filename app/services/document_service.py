

import os
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document import Document
from app.core.config import settings


class DocumentService:
    

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_document_record(
        self,
        filename: str,
        file_type: str,
        file_size: int,
        description: Optional[str] = None,
    ) -> Document:
        
        doc = Document(
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            description=description,
            status="pending",
        )
        self.db.add(doc)
        await self.db.flush()
        return doc

    async def update_document_status(
        self, doc_id: str, status: str, chunk_count: int = 0
    ) -> Optional[Document]:
        
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        doc = result.scalar_one_or_none()
        if doc:
            doc.status = status
            doc.chunk_count = chunk_count
            if status == "completed":
                doc.processed_at = datetime.utcnow()
        return doc

    async def get_all_documents(self) -> list[Document]:
        
        result = await self.db.execute(
            select(Document).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        
        result = await self.db.execute(
            select(Document).where(Document.id == doc_id)
        )
        return result.scalar_one_or_none()
