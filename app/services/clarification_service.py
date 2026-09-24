"""
Clarification Service — the agentic layer of the assistant.

Instead of answering every question in a single shot, the assistant behaves
like a triage conversation. When a user reports a personal symptom without
enough clinical context, the assistant asks relevant follow-up questions ONE
AT A TIME, gathers the answers across turns, and only then retrieves and
answers.

Definition or general-knowledge questions (for example "what is diabetes")
are NOT clarified — those are answered directly.
"""

import random
import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ClarificationResult:
    """Outcome of the clarification check for a user message."""
    needs_clarification: bool
    follow_up_message: Optional[str] = None
    topic: Optional[str] = None
    # Zero-based index of the next question to ask after this turn.
    next_index: int = 0


class ClarificationService:
    """Decides when to ask follow-up questions and what to ask, one at a time.

    The follow-up questions are generated dynamically by the LLM so the
    conversation feels natural — the assistant reads what the patient has
    already said and asks the single most useful next question, phrased
    freshly each time, instead of replaying a fixed script. A curated list of
    essential clinical checkpoints per symptom keeps the LLM on track and acts
    as a fallback when the model is unavailable.
    """

    # Lazily-built chat LLM, shared across calls.
    _llm = None
    _llm_tried = False

    # Essential clinical checkpoints per symptom. These guide the LLM (so it
    # covers the ground a clinician would) and are used verbatim as a fallback
    # when the LLM is unavailable. The LLM rephrases and adapts them to the
    # conversation rather than reading them out word-for-word.
    SYMPTOM_QUESTIONS = {
        "headache": [
            "How long have you had the headache — hours, days, or weeks?",
            "Did it come on suddenly or gradually?",
            "Where is the pain — one side, both sides, forehead, or the back of the head?",
            "How would you rate the pain from 1 to 10?",
            "Do you have any other symptoms such as fever, a stiff neck, vision changes, nausea, or vomiting?",
            "Do you know your current blood pressure reading? (high blood pressure can cause headaches)",
        ],
        "fever": [
            "What is your current temperature, if you have measured it?",
            "How many days have you had the fever?",
            "Is the fever constant, or does it come and go?",
            "Do you have any other symptoms such as cough, sore throat, body aches, chills, or a rash?",
            "Have you had any recent travel, infection, or contact with someone who was ill?",
        ],
        "chest": [
            "How long have you been feeling this?",
            "How would you describe it — pressure, tightness, burning, or sharp pain?",
            "Does the discomfort spread to your arm, jaw, neck, or back?",
            "Do you have any shortness of breath, sweating, nausea, or dizziness along with it?",
            "Does it get worse with activity or when you breathe deeply?",
        ],
        "cough": [
            "How long have you had the cough — days or weeks?",
            "Is it a dry cough, or are you bringing up phlegm? If so, what colour?",
            "Do you also have a fever, sore throat, or difficulty breathing?",
            "Is there any wheezing, chest pain, or blood in what you cough up?",
        ],
        "stomach": [
            "Where exactly is the pain located — upper, lower, right, or left?",
            "How long has it lasted, and how severe is it from 1 to 10?",
            "How would you describe it — cramping, burning, dull, or sharp?",
            "Do you have any nausea, vomiting, fever, or change in bowel habits (diarrhoea or constipation)?",
            "Does anything make it better or worse, such as eating or passing stool?",
        ],
        "dizzy": [
            "How long have you been feeling dizzy?",
            "Is it a spinning sensation (vertigo), or more of a lightheaded / faint feeling?",
            "Does it happen when you stand up, or is it there all the time?",
            "Do you have any other symptoms such as headache, nausea, fainting, or weakness?",
            "Do you know your current blood pressure or blood sugar reading?",
        ],
        "tired": [
            "How long have you been feeling this way?",
            "Is the tiredness constant, or worse at particular times of day?",
            "Do you have any other symptoms such as weight change, fever, poor sleep, or low mood?",
            "Have you had any changes in appetite, thirst, or urination?",
            "Do you know your recent blood pressure or blood sugar readings?",
        ],
        "body_pain": [
            "How long have you had the body pain — a day, several days, or longer?",
            "Which parts of your body are affected — muscles, joints, or all over?",
            "How would you rate the pain from 1 to 10?",
            "Do you have any other symptoms such as fever, headache, chills, cough, or a sore throat?",
            "Have you had any recent illness, strenuous activity, or injury?",
        ],
        "throat": [
            "How long have you had the sore throat?",
            "Do you have pain or difficulty when swallowing?",
            "Do you also have a fever, cough, or swollen glands in your neck?",
            "Have you noticed any white patches or redness at the back of your throat?",
        ],
        "breathing": [
            "How long have you had difficulty breathing?",
            "Did it start suddenly or gradually?",
            "Is it worse with activity, lying down, or at rest?",
            "Do you have any chest pain, cough, wheezing, or swelling in your legs?",
        ],
        "pain": [
            "Where is the pain located?",
            "How long have you had it, and how severe is it from 1 to 10?",
            "How would you describe it — dull, sharp, burning, or throbbing?",
            "Do you have any other symptoms along with the pain, such as fever, swelling, or numbness?",
            "Does anything make it better or worse?",
        ],
    }

    # Alternate spellings / phrasings mapped to their canonical topic above.
    # This catches "head ache", "headaches", "stomach ache", "loose motion", etc.
    SYMPTOM_SYNONYMS = {
        "headache": ["headache", "head ache", "head-ache", "headaches", "migraine"],
        "fever": ["fever", "temperature", "high temp", "feverish"],
        "chest": ["chest pain", "chest", "chest tightness"],
        "cough": ["cough", "coughing"],
        "stomach": [
            "stomach", "stomach ache", "stomach pain", "tummy",
            "abdominal", "abdomen", "belly",
        ],
        "dizzy": ["dizzy", "dizziness", "lightheaded", "light headed", "giddy"],
        "tired": ["tired", "fatigue", "fatigued", "weakness", "exhausted"],
        # Whole-body aches get their own topic so we ask about associated
        # symptoms (fever, headache, chills) rather than just location.
        "body_pain": [
            "body pain", "body pains", "body ache", "body aches",
            "bodyache", "body paining", "muscle pain", "muscle ache",
            "joint pain", "joint pains", "pain all over", "aching all over",
        ],
        "throat": ["sore throat", "throat pain", "throat ache", "throat"],
        "breathing": [
            "shortness of breath", "difficulty breathing", "trouble breathing",
            "breathless", "hard to breathe", "cannot breathe", "can't breathe",
        ],
        # Generic single-word "pain" — checked last, and only wins when no
        # more specific phrase above matched (longest-match wins in _detect_topic).
        "pain": ["pain", "ache", "aching"],
    }

    # First-person phrasing that signals the user is describing THEIR OWN symptom.
    PERSONAL_MARKERS = [
        r"\bi\s+(have|have\s+a|am\s+having|'?m\s+having|feel|'?m\s+feeling|got|'?ve\s+got|'?ve\s+been)\b",
        r"\bi\s+am\b",
        r"\bmy\s+(head|chest|stomach|throat|body|back)\b",
        r"\bi'?m\b",
        r"\bhaving\s+(a\s+)?(head\s*ache|headache|fever|cough|pain)\b",
        r"\bi\s+got\b",
    ]

    # Phrasing that signals a definition / general-knowledge question (never clarified).
    DEFINITION_MARKERS = [
        r"\bwhat\s+is\b",
        r"\bwhat\s+are\b",
        r"\bwhat'?s\b",
        r"\bdefine\b",
        r"\btell\s+me\s+about\b",
        r"\bexplain\b",
        r"\bhow\s+(does|do|is|are)\b",
        r"\bcauses?\s+of\b",
        r"\bsymptoms?\s+of\b",
        r"\btreatment\s+for\b",
        r"\bmeaning\s+of\b",
    ]

    # Detects the symptom topic in the user's message, matching common
    # spelling and phrasing variants (e.g. "head ache" -> "headache").
    def _detect_topic(self, message: str) -> Optional[str]:
        text = message.lower()
        # Check the more specific synonyms first (longest phrases win).
        best_topic = None
        best_len = 0
        for topic, phrases in self.SYMPTOM_SYNONYMS.items():
            for phrase in phrases:
                if phrase in text and len(phrase) > best_len:
                    best_topic = topic
                    best_len = len(phrase)
        return best_topic

    # True when the message is phrased as a definition / general question.
    def _is_definition_question(self, message: str) -> bool:
        text = message.lower()
        for pattern in self.DEFINITION_MARKERS:
            if re.search(pattern, text):
                return True
        return False

    # True when the message describes the user's own symptom (first person).
    def _is_personal_symptom(self, message: str) -> bool:
        text = message.lower()
        for pattern in self.PERSONAL_MARKERS:
            if re.search(pattern, text):
                return True
        return False

    # ---- LLM-backed question generation -------------------------------------

    # How many follow-up questions to ask before answering. Capped so the
    # triage doesn't drag on. We ask up to the number of essential checkpoints
    # for the topic, but never more than this.
    MAX_QUESTIONS = 4

    # Varied, natural lead-ins so the assistant doesn't repeat "Thanks."
    _FIRST_LEADS = [
        "I can help with that.",
        "Sorry to hear that — let me help.",
        "Okay, let's figure this out together.",
        "I'd like to understand this a bit better.",
    ]
    _NEXT_LEADS = [
        "Got it.",
        "Thanks for that.",
        "Okay.",
        "I see.",
        "That's helpful.",
        "Understood.",
        "Alright.",
    ]

    @classmethod
    def _get_llm(cls):
        """Lazily build (and cache) the chat LLM; returns None if unavailable."""
        if cls._llm is None and not cls._llm_tried:
            cls._llm_tried = True
            try:
                from app.services.llm_factory import build_chat_llm

                cls._llm = build_chat_llm(temperature=0.5, num_predict=60)
            except Exception:
                cls._llm = None
        return cls._llm

    @staticmethod
    def _clean_question(text: str) -> str:
        """Trim the model output to a single, tidy question."""
        if not text:
            return ""
        t = text.strip().strip('"').strip()
        # Keep only the first line / first question the model produced.
        t = t.splitlines()[0].strip()
        # Drop any leading "Question:" or numbering artifacts.
        t = re.sub(r"^\s*(question|q)\s*[:\-.]\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"^\s*\d+[.)]\s*", "", t)
        return t.strip()

    def _llm_question(
        self,
        topic: str,
        dialogue: str,
        already_asked: List[str],
        target_checkpoint: str,
    ) -> Optional[str]:
        """
        Ask the LLM to REPHRASE one specific clinical checkpoint into a natural,
        conversational question that fits what the patient has said so far.

        The checkpoint (chosen deterministically by the caller) fixes WHICH
        clinical detail to ask about, so coverage is guaranteed and the small
        model can't drift or repeat. The LLM only controls the wording, giving
        the exchange a human feel. Returns None on any failure so the caller
        can fall back to the checkpoint text verbatim.
        """
        llm = self._get_llm()
        if llm is None:
            return None

        prompt = (
            "You are a warm, friendly medical intake assistant talking with a "
            "patient. Rephrase the clinical question below into ONE natural, "
            "conversational question, taking into account what the patient has "
            "already told you. Keep the SAME clinical meaning.\n\n"
            f"Symptom area: {topic.replace('_', ' ')}\n\n"
            "What the patient has said so far:\n"
            f"{dialogue}\n\n"
            f"Clinical question to rephrase: {target_checkpoint}\n\n"
            "Rules:\n"
            "- Output ONE question only, under 25 words.\n"
            "- Keep the same clinical intent as the question above.\n"
            "- Plain, kind language — no jargon, no diagnosis, no advice.\n"
            "- No preamble or explanation — output only the question.\n\n"
            "Rephrased question:"
        )

        try:
            resp = llm.invoke(prompt)
            content = getattr(resp, "content", None) or str(resp)
            question = self._clean_question(content)
            if not question or "?" not in question:
                return None
            # Guard against the model echoing an earlier question verbatim.
            lowered = question.lower()
            for prev in already_asked:
                if prev and lowered == prev.lower():
                    return None
            return question
        except Exception:
            return None

    # Wraps a single question in a short, conversational lead-in. The lead-in
    # is randomised so consecutive turns don't all start with "Thanks.".
    def _phrase(self, question: str, index: int) -> str:
        q = question.strip()
        if index == 0:
            lead = random.choice(self._FIRST_LEADS)
            body = f"{q[0].lower()}{q[1:]}" if q else q
            return f"{lead} To point you to the right information — {body}"
        lead = random.choice(self._NEXT_LEADS)
        return f"{lead} {q}"

    # Chooses the next question: LLM-generated when possible, otherwise the
    # scripted checkpoint at this position.
    #
    # asked_questions: the ACTUAL questions already put to the patient this
    #                  sequence (LLM-worded), so we don't repeat them. Falls
    #                  back to the scripted checkpoints when not supplied.
    def _next_question(
        self,
        topic: str,
        index: int,
        dialogue: str,
        asked_questions: Optional[List[str]] = None,
    ) -> Optional[str]:
        checkpoints = self.SYMPTOM_QUESTIONS.get(topic, [])
        if index >= len(checkpoints):
            return None

        # The checkpoint at this position fixes WHICH detail to ask next, so
        # coverage is guaranteed and questions never repeat or drift. The LLM
        # only rephrases it to sound natural.
        target = checkpoints[index]
        already_asked = asked_questions if asked_questions else checkpoints[:index]
        generated = self._llm_question(
            topic=topic,
            dialogue=dialogue or "(no details yet)",
            already_asked=already_asked,
            target_checkpoint=target,
        )
        # Fall back to the scripted checkpoint if the LLM produced nothing.
        return generated or target

    # Main entry point — decides whether to ask the next follow-up question.
    #
    # asked_count: how many clarification questions have already been asked in
    #              this conversation (0 if none yet).
    # dialogue:    the patient's words so far (used to generate a natural
    #              question). For a fresh message this is just that message.
    def check(
        self, message: str, asked_count: int, dialogue: str = ""
    ) -> ClarificationResult:
        # Still in the middle of a clarification sequence started earlier.
        if asked_count > 0:
            # We don't know the topic here, so the caller passes it back via
            # continue_topic(). This branch is handled by continue_topic().
            return ClarificationResult(needs_clarification=False)

        topic = self._detect_topic(message)

        # No recognised symptom topic — answer directly.
        if not topic:
            return ClarificationResult(needs_clarification=False)

        # Definition / general questions are answered directly, never clarified.
        if self._is_definition_question(message):
            return ClarificationResult(needs_clarification=False, topic=topic)

        # Only clarify when the user is describing their OWN symptom.
        if not self._is_personal_symptom(message):
            return ClarificationResult(needs_clarification=False, topic=topic)

        question = self._next_question(topic, 0, dialogue or message)
        if not question:
            return ClarificationResult(needs_clarification=False, topic=topic)

        return ClarificationResult(
            needs_clarification=True,
            follow_up_message=self._phrase(question, 0),
            topic=topic,
            next_index=1,
        )

    # Continues an in-progress clarification: asks the next question, or signals
    # that all questions are answered and it's time to retrieve an answer.
    #
    # dialogue: everything the patient has said in this sequence so far, so the
    #           LLM can ask a question that follows on naturally.
    def continue_topic(
        self,
        topic: str,
        asked_count: int,
        dialogue: str = "",
        asked_questions: Optional[List[str]] = None,
    ) -> ClarificationResult:
        checkpoints = self.SYMPTOM_QUESTIONS.get(topic, [])

        # Stop once we've asked enough — either exhausted the checkpoints or
        # hit the cap — and answer.
        limit = min(len(checkpoints), self.MAX_QUESTIONS)
        if asked_count >= limit:
            return ClarificationResult(needs_clarification=False, topic=topic)

        question = self._next_question(
            topic, asked_count, dialogue, asked_questions=asked_questions
        )
        if not question:
            return ClarificationResult(needs_clarification=False, topic=topic)

        return ClarificationResult(
            needs_clarification=True,
            follow_up_message=self._phrase(question, asked_count),
            topic=topic,
            next_index=asked_count + 1,
        )
