"""
Conversation Repository
========================
Handles all database operations for conversations and messages.
Provides a clean interface for the service layer to persist chat data.
"""

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.conversation import Conversation, Message, MessageRole


class ConversationRepository:
    """Repository for Conversation and Message persistence."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, conversation_id: str) -> Optional[Conversation]:
        """Fetch a conversation by its ID."""
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user_id: str, title: str = "New Conversation") -> Conversation:
        """Create a new conversation record."""
        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    async def get_or_create(
        self, user_id: str, conversation_id: Optional[str] = None, title: str = "New Conversation"
    ) -> Conversation:
        """Get existing conversation or create a new one."""
        if conversation_id:
            existing = await self.get_by_id(conversation_id)
            if existing:
                return existing
        return await self.create(user_id, title)

    async def add_message(
        self, conversation_id: str, role: MessageRole, content: str
    ) -> Message:
        """Add a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
        )
        self.db.add(message)
        await self.db.flush()
        return message

    async def get_user_conversations(self, user_id: str) -> list[Conversation]:
        """Get all conversations for a user, most recent first."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())
