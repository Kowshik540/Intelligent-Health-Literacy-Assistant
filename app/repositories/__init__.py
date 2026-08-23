"""
Repository Layer
=================
Encapsulates database access logic, providing a clean abstraction
between the service layer and the ORM. This follows the Repository
Pattern from Domain-Driven Design (DDD).

Each repository handles CRUD operations for a single aggregate root.
"""

from app.repositories.conversation_repository import ConversationRepository
from app.repositories.document_repository import DocumentRepository
from app.repositories.feedback_repository import FeedbackRepository

__all__ = ["ConversationRepository", "DocumentRepository", "FeedbackRepository"]
