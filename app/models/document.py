"""
Document Model
===============
Represents a medical document in the ingestion pipeline.
Tracks the full lifecycle: upload → validation → admin approval → ChromaDB indexing.

Only documents with admin_approved=True are indexed in the vector store.
This prevents unverified content from appearing in search results.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Document(Base):
    """Medical document with validation and approval tracking."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # File metadata
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    # Processing status
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending_validation")

    # Validation metadata
    file_hash: Mapped[str] = mapped_column(String(64), nullable=True)
    publisher: Mapped[str] = mapped_column(String(255), nullable=True)
    isbn_reference: Mapped[str] = mapped_column(String(100), nullable=True)
    source_trusted: Mapped[bool] = mapped_column(Boolean, nullable=True)
    validation_notes: Mapped[str] = mapped_column(Text, nullable=True)

    # Admin approval
    admin_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[str] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Document(id={self.id}, filename={self.filename}, status={self.status})>"
