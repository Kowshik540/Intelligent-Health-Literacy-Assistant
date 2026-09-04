"""
Chat Routes — Handles user messages, conversation history, and AI responses.
"""

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.conversation import (
    ChatRequest, ChatResponse, MessageResponse, CitationDetail,
    ConversationResponse, ConversationWithMessages,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["Chat"])

# Default user ID for demo — in production this comes from authentication
DEFAULT_USER_ID = "default-user-001"


# Receives a user's health question, runs it through the full RAG pipeline, and returns the answer with citations
@router.post("/", response_model=ChatResponse)
async def send_message(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    service = ChatService(db)

    result = await service.process_message(
        user_id=DEFAULT_USER_ID,
        message=request.message,
        conversation_id=request.conversation_id,
    )

    citations = [
        CitationDetail(**c) for c in result.get("citations", [])
    ]

    return ChatResponse(
        conversation_id=result["conversation_id"],
        message=MessageResponse.model_validate(result["message"]),
        sources=result["sources"],
        citations=citations,
        clinical_answer=result["clinical_answer"],
        simplified_answer=result["simplified_answer"],
        is_emergency=result["is_emergency"],
        pii_detected=result["pii_detected"],
    )


# Fetches all past conversations for the current user to display in chat history
@router.get("/conversations", response_model=list[ConversationResponse])
async def get_conversations(db: AsyncSession = Depends(get_db)):
    service = ChatService(db)
    conversations = await service.get_user_conversations(DEFAULT_USER_ID)
    return [ConversationResponse.model_validate(c) for c in conversations]


# Retrieves a specific conversation with all its messages for replay/review
@router.get("/conversations/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(conversation_id: str, db: AsyncSession = Depends(get_db)):
    service = ChatService(db)
    conversation = await service.get_conversation_history(conversation_id)

    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    response = ConversationWithMessages.model_validate(conversation)

    # Strip the internal clarification marker (e.g. [[CLARIFY:fever:2]]) before
    # returning history so it never appears in the UI.
    for msg in response.messages:
        msg.content = re.sub(r"\[\[CLARIFY:[^\]]*\]\]", "", msg.content)

    return response
