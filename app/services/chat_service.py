"""
Chat Service — Main orchestrator for the entire query processing pipeline.
Coordinates: Guardrails → RAG Retrieval → LLM Generation → Simplification → Validation → Persistence

This is the "brain" of the application — every user message flows through here.
"""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.conversation import Conversation, Message, MessageRole
from app.services.rag_service import RAGService
from app.services.guardrails_service import GuardrailsService
from app.services.jargon_simplifier import JargonSimplifier

# Module-level singleton — embedding model loads once, reused across all requests
_rag_singleton = None


# Returns the shared RAG service instance (avoids reloading the 400MB embedding model per request)
def _get_rag_service():
    global _rag_singleton
    if _rag_singleton is None:
        _rag_singleton = RAGService()
    return _rag_singleton


class ChatService:
    """Orchestrates the full message processing pipeline from query to response."""

    # Initializes with a database session and creates guardrails instance
    def __init__(self, db: AsyncSession):
        self.db = db
        self._guardrails = GuardrailsService()
        self._simplifier = None

    # Returns the shared RAG service singleton
    @property
    def rag_service(self):
        return _get_rag_service()

    # Lazy-loads the jargon simplifier (only created when first needed)
    @property
    def simplifier(self):
        if self._simplifier is None:
            self._simplifier = JargonSimplifier()
        return self._simplifier

    # Gets an existing conversation by ID or creates a new one
    async def get_or_create_conversation(
        self, user_id: str, conversation_id: Optional[str] = None, title: str = "New Conversation"
    ) -> Conversation:
        if conversation_id:
            result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conversation = result.scalar_one_or_none()
            if conversation:
                return conversation

        conversation = Conversation(user_id=user_id, title=title)
        self.db.add(conversation)
        await self.db.flush()
        return conversation

    # Main pipeline: guardrails → RAG → simplification → save to DB → return response
    async def process_message(
        self, user_id: str, message: str, conversation_id: Optional[str] = None
    ) -> dict:
        # Step 1: Run safety guardrails (emergency detection + PII sanitization)
        guardrail_result = self._guardrails.check_query(message)

        # If emergency detected, return emergency response immediately
        if not guardrail_result.is_safe:
            conversation = await self.get_or_create_conversation(
                user_id=user_id, conversation_id=conversation_id, title=message[:50]
            )

            user_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=message,
            )
            self.db.add(user_msg)
            await self.db.flush()

            ai_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=guardrail_result.refusal_message,
            )
            self.db.add(ai_msg)
            await self.db.flush()

            return {
                "conversation_id": conversation.id,
                "message": ai_msg,
                "sources": [],
                "citations": [],
                "is_emergency": True,
                "pii_detected": False,
                "clinical_answer": guardrail_result.refusal_message,
                "simplified_answer": guardrail_result.refusal_message,
            }

        # Step 2: Use the sanitized query (PII removed) for RAG retrieval
        sanitized_query = guardrail_result.sanitized_query

        # Step 3: Search ChromaDB and generate answer from retrieved documents
        rag_response = await self.rag_service.get_response(
            question=sanitized_query,
            conversation_id=conversation_id,
        )

        clinical_answer = rag_response["answer"]

        # Step 4: Ensure citations are appended if the LLM didn't include them
        clinical_answer = self._verify_citations(clinical_answer, rag_response.get("citations", []))

        # Step 5: Simplify the clinical answer into plain language
        simplified_answer = await self.simplifier.simplify(clinical_answer)

        # Step 6: Validate the simplification (cosine similarity ≥ 0.85, citations preserved)
        simplified_answer = await self._validate_simplification(
            clinical_answer, simplified_answer
        )

        # Step 7: Persist the conversation and messages to PostgreSQL
        conversation = await self.get_or_create_conversation(
            user_id=user_id, conversation_id=conversation_id, title=message[:50]
        )

        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=sanitized_query,
        )
        self.db.add(user_msg)
        await self.db.flush()

        ai_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=simplified_answer,
        )
        self.db.add(ai_msg)
        await self.db.flush()

        return {
            "conversation_id": conversation.id,
            "message": ai_msg,
            "sources": rag_response.get("sources", []),
            "citations": rag_response.get("citations", []),
            "is_emergency": False,
            "pii_detected": guardrail_result.pii_detected,
            "clinical_answer": clinical_answer,
            "simplified_answer": simplified_answer,
        }

    # Ensures every answer has a citation — appends one if the LLM forgot to include it
    def _verify_citations(self, answer: str, citations: list) -> str:
        if "I cannot provide information" in answer:
            return answer
        if not citations:
            return answer
        if "[Source:" not in answer and "[source:" not in answer.lower():
            sources_text = "; ".join(
                f"[Source: {c['source']}, Page: {c['page_number']}, Section: {c['section_header']}]"
                for c in citations[:2]
            )
            answer = answer + f"\n\n{sources_text}"
        return answer

    # Validates that simplified text preserves meaning (cosine ≥ 0.85) and keeps citations intact
    async def _validate_simplification(
        self, clinical: str, simplified: str, max_retries: int = 2
    ) -> str:
        import re
        import numpy as np

        # Extracts all [Source: ...] citation tags from text
        def extract_citations(text: str) -> set:
            return set(re.findall(r"\[Source:[^\]]+\]", text, re.IGNORECASE))

        # Checks that all citations from the original are present in the simplified version
        def citations_preserved(clinical_text: str, simplified_text: str) -> bool:
            original_cites = extract_citations(clinical_text)
            if not original_cites:
                return True
            simplified_cites = extract_citations(simplified_text)
            return original_cites.issubset(simplified_cites)

        # Computes cosine similarity between two texts using the BGE embedding model
        def cosine_similarity(text_a: str, text_b: str) -> float:
            try:
                embeddings = self.rag_service.embeddings
                vec_a = embeddings.embed_query(text_a)
                vec_b = embeddings.embed_query(text_b)
                a = np.array(vec_a)
                b = np.array(vec_b)
                return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))
            except Exception:
                # Fallback to Jaccard word overlap if embedding fails
                words_a = set(text_a.lower().split())
                words_b = set(text_b.lower().split())
                if not words_a or not words_b:
                    return 0.0
                return len(words_a & words_b) / len(words_a | words_b)

        # Threshold from project documentation Section 5.7
        SIMILARITY_THRESHOLD = 0.85

        current_simplified = simplified
        for attempt in range(max_retries):
            cites_ok = citations_preserved(clinical, current_simplified)
            sim = cosine_similarity(clinical, current_simplified)

            # Pass if both checks succeed
            if cites_ok and sim >= SIMILARITY_THRESHOLD:
                return current_simplified

            # Retry simplification if validation fails
            try:
                current_simplified = await self.simplifier.simplify(clinical)
            except Exception:
                break

        # If all retries fail, return the original clinical answer (safe fallback)
        return clinical

    # Fetches a conversation with all its messages for the history view
    async def get_conversation_history(self, conversation_id: str) -> Optional[Conversation]:
        result = await self.db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        return result.scalar_one_or_none()

    # Gets all conversations for a user, ordered by most recent first
    async def get_user_conversations(self, user_id: str) -> list[Conversation]:
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
        )
        return list(result.scalars().all())
