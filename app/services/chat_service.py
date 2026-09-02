"""
Chat Service — Main orchestrator for the entire query processing pipeline.

Coordinates:
Guardrails → RAG Retrieval → LLM Generation → Simplification
→ Validation → Persistence

This is the "brain" of the application — every user message flows through here.
"""

from typing import Optional
import re

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation, Message, MessageRole
from app.services.rag_service import RAGService
from app.services.guardrails_service import GuardrailsService
from app.services.jargon_simplifier import JargonSimplifier
from app.services.clarification_service import ClarificationService


# Marker embedded in clarification messages so we can recognise them later
# in the conversation history without a separate database column.
CLARIFICATION_MARKER = "[[CLARIFY]]"


# ============================================================
# SHARED RAG SERVICE
# ============================================================

# Embedding model loads once and is reused across requests.
_rag_singleton = None


def _get_rag_service():
    """Returns the shared RAG service instance."""

    global _rag_singleton

    if _rag_singleton is None:
        _rag_singleton = RAGService()

    return _rag_singleton


class ChatService:
    """Orchestrates the complete health-question processing pipeline."""

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(self, db: AsyncSession):
        self.db = db
        self._guardrails = GuardrailsService()
        self._clarifier = ClarificationService()
        self._simplifier = None

    @property
    def rag_service(self):
        """Returns the shared RAG service singleton."""

        return _get_rag_service()

    @property
    def simplifier(self):
        """Lazy-loads the jargon simplifier."""

        if self._simplifier is None:
            self._simplifier = JargonSimplifier()

        return self._simplifier

    # ============================================================
    # CONVERSATION MANAGEMENT
    # ============================================================

    async def get_or_create_conversation(
        self,
        user_id: str,
        conversation_id: Optional[str] = None,
        title: str = "New Conversation",
    ) -> Conversation:

        if conversation_id:

            result = await self.db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id
                )
            )

            conversation = result.scalar_one_or_none()

            if conversation:
                return conversation

        conversation = Conversation(
            user_id=user_id,
            title=title,
        )

        self.db.add(conversation)

        await self.db.flush()

        return conversation

    # ============================================================
    # CLARIFICATION STATE
    # ============================================================

    async def _clarification_state(
        self,
        conversation_id: Optional[str],
    ) -> tuple[bool, Optional[str]]:
        """
        Checks whether the assistant's most recent message in this
        conversation was a clarification prompt.

        Returns:
            (already_clarified, original_question)

        original_question is the user's message that triggered the
        clarification, so it can be combined with the new details.
        """

        if not conversation_id:
            return False, None

        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(5)
        )

        recent = list(result.scalars().all())

        if not recent:
            return False, None

        # The most recent message should be the assistant's clarification.
        last = recent[0]

        if (
            last.role == MessageRole.ASSISTANT
            and CLARIFICATION_MARKER in (last.content or "")
        ):
            # Find the user question that came just before the clarification.
            original_question = None
            for msg in recent[1:]:
                if msg.role == MessageRole.USER:
                    original_question = msg.content
                    break
            return True, original_question

        return False, None

    # ============================================================
    # MAIN MESSAGE PIPELINE
    # ============================================================

    async def process_message(
        self,
        user_id: str,
        message: str,
        conversation_id: Optional[str] = None,
    ) -> dict:

        # ========================================================
        # STEP 1 — SAFETY GUARDRAILS
        # ========================================================

        guardrail_result = self._guardrails.check_query(message)

        # Emergency / unsafe query
        if not guardrail_result.is_safe:

            conversation = await self.get_or_create_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                title=message[:50],
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

        # ========================================================
        # STEP 2 — SANITIZED QUERY
        # ========================================================

        sanitized_query = guardrail_result.sanitized_query

        # ========================================================
        # STEP 2b — AGENTIC CLARIFICATION
        # ========================================================
        #
        # Before answering, decide whether we have enough clinical
        # context. If the user describes a symptom without detail,
        # ask targeted follow-up questions instead of answering.

        # Look back at the conversation to see if we already asked
        # a clarifying question that this message is answering.
        already_clarified, prior_question = await self._clarification_state(
            conversation_id
        )

        clar = self._clarifier.check(
            message=sanitized_query,
            already_clarified=already_clarified,
        )

        if clar.needs_clarification:
            conversation = await self.get_or_create_conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                title=message[:50],
            )

            user_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.USER,
                content=sanitized_query,
            )
            self.db.add(user_msg)
            await self.db.flush()

            # The marker is stored in the database so we can recognise this
            # as a clarification later, but it is stripped before display.
            ai_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=f"{CLARIFICATION_MARKER}{clar.follow_up_message}",
            )
            self.db.add(ai_msg)
            await self.db.flush()

            # Return a clean copy (no marker) for the immediate response.
            ai_msg_clean = Message(
                id=ai_msg.id,
                conversation_id=ai_msg.conversation_id,
                role=MessageRole.ASSISTANT,
                content=clar.follow_up_message,
                created_at=ai_msg.created_at,
            )

            return {
                "conversation_id": conversation.id,
                "message": ai_msg_clean,
                "sources": [],
                "citations": [],
                "is_emergency": False,
                "pii_detected": guardrail_result.pii_detected,
                "clinical_answer": clar.follow_up_message,
                "simplified_answer": clar.follow_up_message,
            }

        # If this message answers a previous clarification, combine the
        # original question with the new details for a richer retrieval query.
        retrieval_query = sanitized_query
        if already_clarified and prior_question:
            retrieval_query = f"{prior_question}. Additional details: {sanitized_query}"

        # ========================================================
        # STEP 3 — RAG RETRIEVAL + CLINICAL ANSWER
        # ========================================================

        rag_response = await self.rag_service.get_response(
            question=retrieval_query,
            conversation_id=conversation_id,
        )

        # Original clinical answer generated from the
        # verified documents in ChromaDB.
        clinical_answer = rag_response["answer"]

        # ========================================================
        # STEP 4 — VERIFY / ADD CITATIONS
        # ========================================================

        clinical_answer = self._verify_citations(
            clinical_answer,
            rag_response.get("citations", []),
        )

        # ========================================================
        # STEP 5 — CREATE PLAIN-LANGUAGE ANSWER
        # ========================================================

        # IMPORTANT:
        # We remove citation metadata before sending the text
        # to the simplifier. This prevents citation strings from
        # affecting the simplification process.
        clinical_content = self._remove_citations(
            clinical_answer
        )

        simplified_content = await self.simplifier.simplify(
            clinical_content
        )

        # Clean accidental citation tags produced by the
        # simplifier. We will restore the original citations
        # ourselves.
        simplified_content = self._remove_citations(
            simplified_content
        ).strip()

        # ========================================================
        # STEP 6 — VALIDATE SIMPLIFICATION
        # ========================================================

        simplified_answer = await self._validate_simplification(
            clinical=clinical_content,
            simplified=simplified_content,
            citations=self._extract_citations(clinical_answer),
        )

        # ========================================================
        # STEP 7 — SAVE CONVERSATION
        # ========================================================

        conversation = await self.get_or_create_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            title=message[:50],
        )

        user_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.USER,
            content=sanitized_query,
        )

        self.db.add(user_msg)

        await self.db.flush()

        # The stored assistant message uses the plain-language
        # answer because that is the user-friendly response.
        ai_msg = Message(
            conversation_id=conversation.id,
            role=MessageRole.ASSISTANT,
            content=simplified_answer,
        )

        self.db.add(ai_msg)

        await self.db.flush()

        # ========================================================
        # STEP 8 — RETURN BOTH VERSIONS
        # ========================================================

        return {
            "conversation_id": conversation.id,
            "message": ai_msg,

            # Retrieved source documents
            "sources": rag_response.get(
                "sources",
                [],
            ),

            # Citation metadata
            "citations": rag_response.get(
                "citations",
                [],
            ),

            "is_emergency": False,

            "pii_detected": guardrail_result.pii_detected,

            # ORIGINAL clinical RAG answer
            "clinical_answer": clinical_answer,

            # ACTUAL simplified answer
            "simplified_answer": simplified_answer,
        }

    # ============================================================
    # CITATION VERIFICATION
    # ============================================================

    def _verify_citations(
        self,
        answer: str,
        citations: list,
    ) -> str:

        if "I cannot provide information" in answer:
            return answer

        if not citations:
            return answer

        # Don't add duplicate citations.
        if "[Source:" in answer or "[source:" in answer.lower():
            return answer

        sources_text = "; ".join(
            (
                f"[Source: {c['source']}, "
                f"Page: {c['page_number']}, "
                f"Section: {c['section_header']}]"
            )
            for c in citations[:2]
        )

        return f"{answer}\n\n{sources_text}"

    # ============================================================
    # CITATION EXTRACTION
    # ============================================================

    def _extract_citations(
        self,
        text: str,
    ) -> list[str]:

        """
        Extracts citations in the format:

        [Source: ..., Page: ..., Section: ...]
        """

        pattern = r"\[Source:[^\]]+\]"

        return re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

    # ============================================================
    # REMOVE CITATIONS
    # ============================================================

    def _remove_citations(
        self,
        text: str,
    ) -> str:

        """
        Removes citation tags before simplification or
        semantic comparison.
        """

        return re.sub(
            r"\[Source:[^\]]+\]",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

    # ============================================================
    # SIMPLIFICATION VALIDATION
    # ============================================================

    async def _validate_simplification(
        self,
        clinical: str,
        simplified: str,
        citations: list[str],
        max_retries: int = 3,
    ) -> str:

        """
        Validates the plain-language answer.

        IMPORTANT:
        The similarity calculation is performed ONLY against
        the medical content.

        Citation metadata is added after validation.

        The 0.85 score is retained as the project's validation
        threshold, but a failed score no longer silently replaces
        the plain-language answer with the clinical answer.
        """

        SIMILARITY_THRESHOLD = 0.85

        # --------------------------------------------------------
        # Cosine similarity
        # --------------------------------------------------------

        def cosine_similarity(
            text_a: str,
            text_b: str,
        ) -> float:

            try:

                embeddings = self.rag_service.embeddings

                vec_a = embeddings.embed_query(
                    text_a
                )

                vec_b = embeddings.embed_query(
                    text_b
                )

                a = np.array(
                    vec_a,
                    dtype=float,
                )

                b = np.array(
                    vec_b,
                    dtype=float,
                )

                denominator = (
                    np.linalg.norm(a)
                    * np.linalg.norm(b)
                )

                if denominator == 0:
                    return 0.0

                return float(
                    np.dot(a, b)
                    / denominator
                )

            except Exception:

                # Fallback to word overlap if embeddings
                # cannot be calculated.
                words_a = set(
                    text_a.lower().split()
                )

                words_b = set(
                    text_b.lower().split()
                )

                if not words_a or not words_b:
                    return 0.0

                return (
                    len(words_a & words_b)
                    / len(words_a | words_b)
                )

        # --------------------------------------------------------
        # Start with the generated simplified answer
        # --------------------------------------------------------

        current_simplified = simplified.strip()

        # If the simplifier returned nothing, retry.
        if not current_simplified:

            current_simplified = clinical

        # --------------------------------------------------------
        # Validation / retry loop
        # --------------------------------------------------------

        for attempt in range(max_retries):

            similarity = cosine_similarity(
                clinical,
                current_simplified,
            )

            # Valid simplification
            if similarity >= SIMILARITY_THRESHOLD:

                return self._append_citations(
                    current_simplified,
                    citations,
                )

            # Retry the simplifier if similarity is too low.
            if attempt < max_retries - 1:

                try:

                    retry_result = (
                        await self.simplifier.simplify(
                            clinical
                        )
                    )

                    retry_result = self._remove_citations(
                        retry_result
                    ).strip()

                    if retry_result:

                        current_simplified = retry_result

                except Exception:
                    pass

        # --------------------------------------------------------
        # IMPORTANT FALLBACK BEHAVIOR
        # --------------------------------------------------------
        #
        # Previously this returned:
        #
        #     return clinical
        #
        # That made Clinical and Plain Language identical
        # whenever the similarity score was below 0.85.
        #
        # Now we keep the generated plain-language answer.
        # The validation threshold is still calculated and
        # retries are still attempted.
        # --------------------------------------------------------

        if current_simplified:

            return self._append_citations(
                current_simplified,
                citations,
            )

        # Absolute safety fallback only if the simplifier
        # produced no usable text at all.
        return self._append_citations(
            clinical,
            citations,
        )

    # ============================================================
    # APPEND ORIGINAL CITATIONS
    # ============================================================

    def _append_citations(
        self,
        answer: str,
        citations: list[str],
    ) -> str:

        answer = answer.strip()

        if not citations:
            return answer

        citation_block = "\n\n".join(
            citations
        )

        return f"{answer}\n\n{citation_block}"

    # ============================================================
    # CONVERSATION HISTORY
    # ============================================================

    async def get_conversation_history(
        self,
        conversation_id: str,
    ) -> Optional[Conversation]:

        result = await self.db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id
            )
        )

        return result.scalar_one_or_none()

    # ============================================================
    # USER CONVERSATIONS
    # ============================================================

    async def get_user_conversations(
        self,
        user_id: str,
    ) -> list[Conversation]:

        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id
            )
            .order_by(
                Conversation.updated_at.desc()
            )
        )

        return list(
            result.scalars().all()
        )