"""
Feedback Repository
====================
Handles persistence for RLHF feedback data.
Supports the Golden Dataset pipeline for future model fine-tuning.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.feedback import Feedback


class FeedbackRepository:
    """Repository for user feedback (thumbs up/down + corrections)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, **kwargs) -> Feedback:
        """Store a new feedback entry."""
        feedback = Feedback(**kwargs)
        self.db.add(feedback)
        await self.db.flush()
        return feedback

    async def get_all(self) -> list[Feedback]:
        """Get all feedback entries."""
        result = await self.db.execute(select(Feedback))
        return list(result.scalars().all())

    async def get_golden_dataset(self) -> list[Feedback]:
        """
        Get negative feedback with user corrections — the Golden Dataset.
        These are used to fine-tune the model on where it made mistakes.
        """
        result = await self.db.execute(
            select(Feedback)
            .where(Feedback.is_positive == False)
            .where(Feedback.user_correction.isnot(None))
            .order_by(Feedback.created_at.desc())
        )
        return list(result.scalars().all())
