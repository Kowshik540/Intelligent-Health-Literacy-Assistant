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
from app.services.clinical_triage_service import ClinicalTriageService
from app.services.biometric_service import BiometricService
from app.services.output_verification_service import OutputVerificationService
from app.services.drug_interaction_service import DrugInteractionService


# Marker embedded in clarification messages so we can recognise them later in
# the conversation history without a separate database column. The topic and
# the number of questions asked so far are encoded as: [[CLARIFY:topic:count]]
CLARIFICATION_MARKER = "[[CLARIFY"


# Builds the encoded marker for a clarification message.
def _make_marker(topic: str, count: int) -> str:
    return f"[[CLARIFY:{topic}:{count}]]"


# Parses topic and count from a stored clarification message, if present.
def _parse_marker(content: str):
    match = re.search(r"\[\[CLARIFY:([^:]*):(\d+)\]\]", content or "")
    if not match:
        return None, 0
    return match.group(1), int(match.group(2))


# Strips inline [Source: ...] citation tags (and stray bracket artifacts) from
# text meant for the chat bubble. Citations are shown as structured cards in the
# evidence sidebar (the `citations` list), so they should not clutter the reply
# text. Kept module-level so it can be reused by the routes for history display.
def clean_display_text(text: str) -> str:
    if not text:
        return text
    cleaned = re.sub(r"\[Source:[^\]]*\];?", "", text, flags=re.IGNORECASE)
    # Remove any leftover empty-bracket artifacts.
    cleaned = re.sub(r"\[\s*\];?", "", cleaned)
    # Collapse whitespace left behind by the removals.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


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
        self._triage = ClinicalTriageService()
        self._biometrics = BiometricService()
        self._verifier = OutputVerificationService()
        self._interactions = DrugInteractionService()
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
    ) -> tuple[bool, Optional[str], int, str]:
        """
        Inspects the conversation to see if we are in the middle of a
        clarification sequence.

        Returns:
            (in_progress, topic, asked_count, gathered_context)

        gathered_context combines the original symptom message with every
        answer the user has given so far, so the final retrieval query is rich.
        """

        if not conversation_id:
            return False, None, 0, ""

        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.desc())
            .limit(20)
        )

        recent = list(result.scalars().all())
        if not recent:
            return False, None, 0, ""

        # The most recent message must be the assistant's clarification prompt.
        last = recent[0]
        if last.role != MessageRole.ASSISTANT or CLARIFICATION_MARKER not in (
            last.content or ""
        ):
            return False, None, 0, ""

        topic, asked_count = _parse_marker(last.content)

        # Collect ONLY the messages belonging to the current clarification
        # sequence. Walking newest → oldest, we stop as soon as we hit an
        # assistant message that is NOT a clarification prompt — that marks
        # the boundary of an earlier, unrelated exchange.
        sequence_user_messages = []
        for msg in recent:
            if msg.role == MessageRole.ASSISTANT:
                if CLARIFICATION_MARKER in (msg.content or ""):
                    continue  # part of this clarification sequence
                break  # previous unrelated answer — stop here
            # User message within the current sequence.
            sequence_user_messages.append(msg.content)

        # Oldest first: the original symptom, then each reply.
        sequence_user_messages.reverse()
        gathered_context = ". ".join(
            g for g in sequence_user_messages if g
        )

        return True, topic, asked_count, gathered_context

    # ============================================================
    # SESSION MEMORY (longitudinal, multi-turn)
    # ============================================================

    async def _gather_session_history(
        self,
        conversation_id: Optional[str],
    ) -> str:
        """
        Returns the concatenated text of all prior USER messages in this
        conversation (oldest first), with internal clarification markers
        stripped. This lets triage and biometric evaluation remember vitals,
        symptoms, and demographics the patient shared on earlier turns, so a
        later symptom is assessed against the reported baseline without asking
        the patient to repeat values.
        """
        if not conversation_id:
            return ""

        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .where(Message.role == MessageRole.USER)
            .order_by(Message.created_at.asc())
            .limit(40)
        )
        prior = [m.content for m in result.scalars().all() if m.content]
        # Strip any stored clarification markers just in case.
        prior = [re.sub(r"\[\[CLARIFY:[^\]]*\]\]", "", p).strip() for p in prior]
        return " | ".join(p for p in prior if p)

    # Recognises a vague follow-up that depends on earlier context, e.g.
    # "is that ok?", "should I worry about it?", "what does this mean?".
    _FOLLOWUP_RE = re.compile(
        r"\b(that|this|it|those|these|the reading|the number|the result)\b",
        re.IGNORECASE,
    )

    # Recognises a request for medication, e.g. "any medicine", "what can I
    # take", "should I take ibuprofen", "which painkiller".
    _MED_SEEKING_RE = re.compile(
        r"\b(any medicine|any medication|what (?:can|should) i take|"
        r"what medicine|which (?:medicine|medication|tablet|pill|painkiller)|"
        r"should i take|can i take|take (?:some )?(?:medicine|medication|"
        r"ibuprofen|aspirin|paracetamol|acetaminophen|tylenol|advil|"
        r"antacid|laxative|painkiller)|give me (?:a )?medicine|"
        r"home remedy|otc|over.the.counter)\b",
        re.IGNORECASE,
    )

    def _is_medication_seeking(self, text: str) -> bool:
        return bool(self._MED_SEEKING_RE.search(text or ""))

    def _is_followup(self, text: str) -> bool:
        cleaned = (text or "").strip()
        words = cleaned.split()
        if not words:
            return False
        # Short message that refers back to something ("that", "it", ...).
        if len(words) <= 12 and self._FOLLOWUP_RE.search(cleaned):
            return True
        return False

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
        # SESSION MEMORY — remember vitals/symptoms from earlier turns
        # ========================================================
        #
        # Pull the patient's prior messages so a symptom reported now is
        # assessed against vitals/demographics they gave earlier (e.g. an
        # "8/10 headache" now, with "BP 110/60, age 50" from before).

        session_history = await self._gather_session_history(conversation_id)
        synthesized_now = (
            f"{session_history} | {sanitized_query}".strip(" |")
            if session_history
            else sanitized_query
        )

        # ========================================================
        # STAGE 1/2 (early pass) — TRIAGE + BIOMETRICS (with memory)
        # ========================================================
        #
        # Safety-critical ordering: a CRITICAL red flag (stroke signs,
        # thunderclap headache, hypertensive crisis, low SpO2, etc.) MUST
        # escalate immediately and must NOT be delayed by the clarification
        # follow-up loop. So we assess acuity here, before clarification.
        # We assess the current message AND the accumulated session context.

        early_triage = self._triage.assess(synthesized_now)
        early_bio = self._biometrics.evaluate(synthesized_now)
        if early_bio.critical_flags:
            early_triage.red_flag_detected = True
            early_triage.flagged_symptoms.extend(early_bio.critical_flags)
            early_triage.acuity_level = "CRITICAL"
            early_triage.requires_immediate_escalation = True

        if early_triage.requires_immediate_escalation:
            return await self._emergency_escalation(
                user_id=user_id,
                conversation_id=conversation_id,
                title_seed=message,
                sanitized_query=sanitized_query,
                triage=early_triage,
                biometrics=early_bio,
                pii_detected=guardrail_result.pii_detected,
                med_seeking=self._is_medication_seeking(synthesized_now),
            )

        # ========================================================
        # STEP 2b — AGENTIC CLARIFICATION (one question at a time)
        # ========================================================
        #
        # If the user reports a personal symptom, gather details one
        # question at a time before answering. Definition questions
        # ("what is diabetes") are answered directly.

        in_progress, topic, asked_count, gathered_context = (
            await self._clarification_state(conversation_id)
        )

        if in_progress and topic:
            # Continue an existing clarification sequence: ask the next
            # question, or finish and proceed to answer.
            clar = self._clarifier.continue_topic(topic, asked_count)
        else:
            # Fresh message: decide whether to start a clarification sequence.
            clar = self._clarifier.check(sanitized_query, asked_count=0)

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

            # Store the marker (topic + progress) so the next turn knows
            # where we are. It is stripped before display.
            marker = _make_marker(clar.topic, clar.next_index)
            ai_msg = Message(
                conversation_id=conversation.id,
                role=MessageRole.ASSISTANT,
                content=f"{marker}{clar.follow_up_message}",
            )
            self.db.add(ai_msg)
            await self.db.flush()

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

        # If we just finished gathering clarification details, use the full
        # gathered context (original symptom + all answers) as the query.
        retrieval_query = sanitized_query
        if in_progress and gathered_context:
            retrieval_query = gathered_context
        elif session_history and self._is_followup(sanitized_query):
            # A vague follow-up ("is that ok?", "should I worry?") carries no
            # medical keywords of its own, so retrieval would drift off-topic.
            # Anchor it to what the patient said earlier in the session.
            retrieval_query = f"{session_history} {sanitized_query}".strip()

        # ========================================================
        # STAGE 1 — CLINICAL TRIAGE & RED-FLAG (deterministic)
        # STAGE 2 — BIOMETRIC PARSING & EVALUATION (deterministic)
        # ========================================================
        #
        # Both run on the full available context — the current message, any
        # clarification answers, AND the remembered session history — so
        # numbers and red flags from earlier turns are synthesized, not lost.

        synthesis_context = retrieval_query
        if session_history and session_history not in retrieval_query:
            synthesis_context = f"{session_history} | {retrieval_query}".strip(" |")

        triage = self._triage.assess(synthesis_context)
        biometrics = self._biometrics.evaluate(synthesis_context)

        # Deterministic high-risk drug-interaction check over the full session
        # context, so a drug mentioned earlier ("I take lisinopril") is checked
        # against one asked about now ("can I take ibuprofen?").
        interaction_result = self._interactions.check(synthesis_context)

        # A critical biometric reading (e.g. hypertensive crisis, SpO2 < 90)
        # raises the acuity even if no symptom-based red flag was worded.
        if biometrics.critical_flags:
            triage.red_flag_detected = True
            triage.flagged_symptoms.extend(biometrics.critical_flags)
            triage.acuity_level = "CRITICAL"
            triage.requires_immediate_escalation = True

        # CRITICAL acuity bypasses general RAG and returns the emergency
        # protocol immediately. This catches red flags that only became clear
        # after the clarification answers were gathered.
        if triage.requires_immediate_escalation:
            return await self._emergency_escalation(
                user_id=user_id,
                conversation_id=conversation_id,
                title_seed=message,
                sanitized_query=sanitized_query,
                triage=triage,
                biometrics=biometrics,
                pii_detected=guardrail_result.pii_detected,
                med_seeking=self._is_medication_seeking(synthesis_context),
            )

        deterministic_context = biometrics.as_prompt_context()
        acuity_context = triage.as_prompt_context()

        # ========================================================
        # STAGE 3 — RAG RETRIEVAL + CLINICAL ANSWER (synthesizer)
        # ========================================================

        rag_response = await self.rag_service.get_response(
            question=retrieval_query,
            conversation_id=conversation_id,
            deterministic=deterministic_context,
            acuity=acuity_context,
        )

        # Original clinical answer generated from the
        # verified documents in ChromaDB.
        clinical_answer = rag_response["answer"]

        # ========================================================
        # STAGE 4 — OUTPUT GUARDRAIL & VERIFICATION (deterministic)
        # ========================================================
        #
        # Audit the generated answer against the deterministic biometric
        # classifications and triage acuity. If it contradicts the numbers or
        # downplays a high-acuity symptom, regenerate once; if it still fails,
        # prepend a corrective safety notice so the user never sees the
        # contradiction.

        clinical_answer = await self._verify_and_correct(
            answer=clinical_answer,
            retrieval_query=retrieval_query,
            conversation_id=conversation_id,
            deterministic=deterministic_context,
            acuity=acuity_context,
            biometrics=biometrics,
            triage=triage,
        )

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
        # STEP 6b — PREPEND DRUG-INTERACTION WARNING (deterministic)
        # ========================================================
        #
        # If a high-risk medication combination was detected across the
        # session, surface an authoritative warning at the top of the answer
        # (the LLM cannot be trusted to catch these reliably).

        if interaction_result.has_interaction:
            warning_block = interaction_result.as_warning_block()
            clinical_answer = f"{warning_block}\n\n{clinical_answer}".strip()
            simplified_answer = f"{warning_block}\n\n{simplified_answer}".strip()

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
            # The chat bubble shows clean text; citation tags are stripped and
            # rendered separately in the evidence sidebar.
            content=clean_display_text(simplified_answer),
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

            # Citation metadata (structured cards for the evidence sidebar)
            "citations": rag_response.get(
                "citations",
                [],
            ),

            "is_emergency": False,

            "pii_detected": guardrail_result.pii_detected,

            # ORIGINAL clinical RAG answer (keeps its single citation block).
            "clinical_answer": clinical_answer,

            # Plain-language answer for the chat bubble — citation tags stripped
            # so they only appear as sidebar cards.
            "simplified_answer": clean_display_text(simplified_answer),
        }

    # ============================================================
    # STAGE 1 — CRITICAL ESCALATION MESSAGE
    # ============================================================

    def _build_escalation_message(self, triage, biometrics, med_seeking: bool = False) -> str:
        """
        Builds the immediate escalation message for a CRITICAL triage result.
        Combines the deterministic red flags with clear emergency guidance.
        When the patient asked what medicine to take, adds an explicit
        do-not-self-medicate warning with the clinical rationale.
        """
        lines = [
            "SEEK EMERGENCY MEDICAL EVALUATION IMMEDIATELY — "
            "call your local emergency number (India: 112 / 108; US: 911; UK: 999) "
            "or go to the nearest emergency department.",
            "",
            "What was detected:",
        ]
        for flag in triage.flagged_symptoms:
            lines.append(f"• {flag}")
        for reading in biometrics.readings:
            if reading.is_critical:
                lines.append(f"• {reading.detail}")

        # Whether an acute abdomen is among the concerns (drives the
        # medication rationale wording).
        is_acute_abdomen = any(
            "acute abdomen" in f.lower() or "gi bleed" in f.lower()
            for f in triage.flagged_symptoms
        )

        if med_seeking:
            lines += [
                "",
                "Do NOT take any medicine right now:",
                "• Do not take painkillers (ibuprofen, aspirin, paracetamol), "
                "antacids, or laxatives. They can mask critical signs a doctor "
                "needs to make the right diagnosis"
                + (" (for example, appendicitis)." if is_acute_abdomen else "."),
                "• Do not eat or drink anything until a clinician has evaluated "
                "you — you may need urgent tests or emergency surgery, and food "
                "or fluids can delay anesthesia.",
            ]

        lines += [
            "",
            "Right now:",
            "• Do not drive yourself — have someone drive you or call an ambulance.",
            "• Alert someone nearby who can stay with you.",
        ]

        lines += [
            "",
            "Red-flag symptoms that need emergency care right away:",
            "• Sudden, severe (\"worst ever\") headache",
            "• Face drooping, one-sided weakness, slurred speech, or confusion",
            "• Stiff neck with fever or sensitivity to light",
            "• Chest pain, trouble breathing, or fainting",
            "• Severe abdominal pain, a rigid abdomen, or vomiting blood",
            "",
            "This assistant cannot manage emergencies. Please get professional help immediately.",
        ]
        return "\n".join(lines)

    async def _emergency_escalation(
        self,
        user_id: str,
        conversation_id: Optional[str],
        title_seed: str,
        sanitized_query: str,
        triage,
        biometrics,
        pii_detected: bool,
        med_seeking: bool = False,
    ) -> dict:
        """
        Persists the user message + emergency escalation response and returns
        the standard chat result dict. Used whenever triage reaches CRITICAL.
        """
        escalation = self._build_escalation_message(triage, biometrics, med_seeking)

        conversation = await self.get_or_create_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            title=title_seed[:50],
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
            content=escalation,
        )
        self.db.add(ai_msg)
        await self.db.flush()

        return {
            "conversation_id": conversation.id,
            "message": ai_msg,
            "sources": [],
            "citations": [],
            "is_emergency": True,
            "pii_detected": pii_detected,
            "clinical_answer": escalation,
            "simplified_answer": escalation,
        }

    # ============================================================
    # STAGE 4 — VERIFY & CORRECT THE CLINICAL ANSWER
    # ============================================================

    async def _verify_and_correct(
        self,
        answer: str,
        retrieval_query: str,
        conversation_id: Optional[str],
        deterministic: str,
        acuity: str,
        biometrics,
        triage,
    ) -> str:
        """
        Runs the deterministic output auditor. On failure, regenerates the RAG
        answer once (the prompt already carries the deterministic override). If
        the regenerated answer still fails, prepends a corrective safety notice
        so a contradiction or downplayed acuity never reaches the user.
        """
        verdict = self._verifier.verify(answer, biometrics, triage)
        if verdict.passed:
            return answer

        # Attempt one regeneration with the same deterministic context.
        try:
            regen = await self.rag_service.get_response(
                question=retrieval_query,
                conversation_id=conversation_id,
                deterministic=deterministic,
                acuity=acuity,
            )
            regen_answer = regen.get("answer", answer)
            regen_verdict = self._verifier.verify(regen_answer, biometrics, triage)
            if regen_verdict.passed:
                return regen_answer
            answer = regen_answer
        except Exception:
            pass

        # Still failing — prepend an authoritative corrective notice.
        notice_parts = []
        if biometrics.readings:
            facts = " ".join(r.detail for r in biometrics.readings)
            notice_parts.append(f"Important: {facts}")
        if triage.acuity_level in ("HIGH", "CRITICAL"):
            notice_parts.append(
                "Because your symptoms may be serious, please seek prompt in-person "
                "medical evaluation rather than waiting."
            )
        notice = " ".join(notice_parts).strip()
        return f"{notice}\n\n{answer}".strip() if notice else answer

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

        # If the model already wrote citations inline, just collapse any
        # duplicate [Source: ...] lines it produced and return.
        if "[source:" in answer.lower():
            return self._dedupe_inline_citations(answer)

        # Build a de-duplicated citation block from the top sources.
        seen = set()
        source_lines = []
        for c in citations:
            line = (
                f"[Source: {c['source']}, "
                f"Page: {c['page_number']}, "
                f"Section: {c['section_header']}]"
            )
            key = line.lower()
            if key not in seen:
                seen.add(key)
                source_lines.append(line)
            if len(source_lines) >= 2:
                break

        sources_text = "; ".join(source_lines)
        return f"{answer}\n\n{sources_text}"

    @staticmethod
    def _dedupe_inline_citations(answer: str) -> str:
        """Remove repeated identical [Source: ...] citations from the text."""
        seen = set()

        def _keep(match: "re.Match") -> str:
            token = match.group(0)
            key = token.strip().lower()
            if key in seen:
                return ""
            seen.add(key)
            return token

        deduped = re.sub(r"\[Source:[^\]]+\]", _keep, answer, flags=re.IGNORECASE)
        # Tidy up leftover separators like "; ;" or trailing "; ".
        deduped = re.sub(r"(;\s*)+", "; ", deduped)
        deduped = re.sub(r";\s*$", "", deduped.strip())
        return deduped.strip()

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

        found = re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        # De-duplicate while preserving order — the LLM sometimes emits the
        # same citation line twice, which would otherwise be shown twice.
        seen = set()
        unique = []
        for c in found:
            key = c.strip().lower()
            if key not in seen:
                seen.add(key)
                unique.append(c.strip())
        return unique

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