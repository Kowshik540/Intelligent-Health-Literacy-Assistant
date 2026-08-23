"""
ORM Models
===========
SQLAlchemy models representing the database schema.
These map directly to PostgreSQL tables and define relationships between entities.

Tables:
- users: Application users
- conversations: Chat sessions belonging to a user
- messages: Individual messages within a conversation
- documents: Ingested medical PDFs with validation metadata
- feedback: RLHF feedback for Golden Dataset generation
"""

from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.document import Document
from app.models.feedback import Feedback

__all__ = ["User", "Conversation", "Message", "Document", "Feedback"]
