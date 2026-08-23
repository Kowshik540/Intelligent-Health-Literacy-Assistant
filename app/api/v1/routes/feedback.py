"""
Feedback Routes — Handles thumbs up/down ratings and the Golden Dataset for RLHF.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.feedback import Feedback
from app.schemas.feedback import (
    FeedbackCreate, FeedbackResponse, GoldenDatasetEntry
)

router = APIRouter(prefix="/feedback", tags=["RLHF Feedback"])


# Stores user feedback (thumbs up/down) on an AI response for quality tracking
@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
):
    db_feedback = Feedback(
        message_id=feedback.message_id,
        conversation_id=feedback.conversation_id,
        is_positive=feedback.is_positive,
        original_question=feedback.original_question,
        ai_answer=feedback.ai_answer,
        user_correction=feedback.user_correction,
        error_category=feedback.error_category,
    )
    db.add(db_feedback)
    await db.flush()

    return FeedbackResponse.model_validate(db_feedback)


# Returns the Golden Dataset — negative feedback with user corrections for future fine-tuning
@router.get("/golden-dataset", response_model=list[GoldenDatasetEntry])
async def get_golden_dataset(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Feedback)
        .where(Feedback.is_positive == False)
        .where(Feedback.user_correction.isnot(None))
        .order_by(Feedback.created_at.desc())
    )
    feedbacks = result.scalars().all()

    return [
        GoldenDatasetEntry(
            question=f.original_question,
            incorrect_answer=f.ai_answer,
            correct_answer=f.user_correction,
            error_category=f.error_category,
            created_at=f.created_at,
        )
        for f in feedbacks
    ]


# Returns aggregated feedback statistics (satisfaction rate, golden dataset size)
@router.get("/stats")
async def get_feedback_stats(db: AsyncSession = Depends(get_db)):
    all_feedback = await db.execute(select(Feedback))
    feedbacks = all_feedback.scalars().all()

    total = len(feedbacks)
    positive = sum(1 for f in feedbacks if f.is_positive)
    negative = total - positive

    return {
        "total_feedback": total,
        "positive": positive,
        "negative": negative,
        "satisfaction_rate": round(positive / total * 100, 1) if total > 0 else 0,
        "golden_dataset_size": sum(
            1 for f in feedbacks if not f.is_positive and f.user_correction
        ),
    }
