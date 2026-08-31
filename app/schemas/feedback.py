

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    
    message_id: str = Field(description="ID of the AI message being rated")
    conversation_id: str = Field(description="ID of the conversation")
    is_positive: bool = Field(description="True = thumbs up, False = thumbs down")
    original_question: str = Field(description="The question that produced this answer")
    ai_answer: str = Field(description="The AI answer being rated")
    user_correction: Optional[str] = Field(
        default=None,
        description="User's correction when thumbs down (for Golden Dataset)"
    )
    error_category: Optional[str] = Field(
        default=None,
        description="Category: incorrect_citation, wrong_information, incomplete, unclear, other"
    )


class FeedbackResponse(BaseModel):
    
    id: str
    message_id: str
    conversation_id: str
    is_positive: bool
    original_question: str
    ai_answer: str
    user_correction: Optional[str] = None
    error_category: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GoldenDatasetEntry(BaseModel):
    
    question: str
    incorrect_answer: str
    correct_answer: str
    error_category: Optional[str] = None
    created_at: datetime
