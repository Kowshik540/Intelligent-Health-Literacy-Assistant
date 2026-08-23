"""
Feedback Model
===============
Stores user feedback (thumbs up/down) on AI responses.
Negative feedback with corrections forms the "Golden Dataset" —
a curated set of question-answer pairs for future model fine-tuning.

This implements the RLHF (Reinforcement Learning from Human Feedback) data
collection pipeline as described in the project documentation.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Feedback(Base):
    """User feedback on AI responses — feeds the Golden Dataset for RLHF."""

    __tablename__ = "feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Reference to the rated message
    message_id: Mapped[str] = mapped_column(String(36), nullable=False)
    conversation_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Rating
    is_positive: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # Context for the Golden Dataset
    original_question: Mapped[str] = mapped_column(Text, nullable=False)
    ai_answer: Mapped[str] = mapped_column(Text, nullable=False)

    # Correction data (populated when thumbs down)
    user_correction: Mapped[str] = mapped_column(Text, nullable=True)
    error_category: Mapped[str] = mapped_column(String(50), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Feedback(id={self.id}, positive={self.is_positive})>"
