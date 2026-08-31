

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class MessageCreate(BaseModel):
    
    content: str = Field(
        min_length=1,
        max_length=5000,
        examples=["What are the symptoms of diabetes?"]
    )


class MessageResponse(BaseModel):
    
    id: str
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class CitationDetail(BaseModel):
    
    source: str
    page_number: str
    section_header: str
    relevance_score: float
    text_snippet: str


class ConversationCreate(BaseModel):
    
    title: Optional[str] = Field(default="New Conversation", max_length=255)


class ConversationResponse(BaseModel):
    
    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    
    messages: list[MessageResponse] = []


class ChatRequest(BaseModel):
    
    message: str = Field(
        min_length=1,
        max_length=5000,
        examples=["Explain hypertension in simple terms"]
    )
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    
    conversation_id: str
    message: MessageResponse
    sources: list[str] = []
    citations: list[CitationDetail] = []
    clinical_answer: str
    simplified_answer: str
    is_emergency: bool = False
    pii_detected: bool = False
