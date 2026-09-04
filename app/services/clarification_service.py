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

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ClarificationResult:
    """Outcome of the clarification check for a user message."""
    needs_clarification: bool
    follow_up_message: Optional[str] = None
    topic: Optional[str] = None
    # Zero-based index of the next question to ask after this turn.
    next_index: int = 0


class ClarificationService:
    """Decides when to ask follow-up questions and what to ask, one at a time."""

    # Each symptom maps to the follow-up questions a clinician would typically ask.
    SYMPTOM_QUESTIONS = {
        "headache": [
            "How long have you had the headache — hours, days, or weeks?",
            "How would you rate the pain from 1 to 10?",
            "Do you have any other symptoms such as fever, vision changes, or nausea?",
        ],
        "fever": [
            "What is your current temperature, if you have measured it?",
            "How many days have you had the fever?",
            "Do you have any other symptoms such as cough, sore throat, or body aches?",
        ],
        "chest": [
            "How long have you been feeling this?",
            "Does the discomfort spread to your arm, jaw, or back?",
            "Do you have any shortness of breath or sweating along with it?",
        ],
        "cough": [
            "How long have you had the cough — days or weeks?",
            "Is it a dry cough, or are you bringing up phlegm?",
            "Do you also have a fever or difficulty breathing?",
        ],
        "stomach": [
            "Where exactly is the pain located?",
            "How long has it lasted, and how severe is it from 1 to 10?",
            "Do you have any nausea, vomiting, or change in bowel habits?",
        ],
        "dizzy": [
            "How long have you been feeling dizzy?",
            "Do you know your current blood pressure reading?",
            "Do you have any other symptoms such as headache, nausea, or fainting?",
        ],
        "tired": [
            "How long have you been feeling this way?",
            "Do you have any other symptoms such as weight change, fever, or low mood?",
            "Do you know your recent blood pressure or blood sugar readings?",
        ],
        "pain": [
            "Where is the pain located?",
            "How long have you had it, and how severe is it from 1 to 10?",
            "Does anything make it better or worse?",
        ],
    }

    # First-person phrasing that signals the user is describing THEIR OWN symptom.
    PERSONAL_MARKERS = [
        r"\bi\s+(have|have\s+a|am\s+having|'?m\s+having|feel|'?m\s+feeling|got|'?ve\s+got|'?ve\s+been)\b",
        r"\bi\s+am\b",
        r"\bmy\s+(head|chest|stomach|throat|body|back)\b",
        r"\bi'?m\b",
        r"\bhaving\s+(a\s+)?(headache|fever|cough|pain)\b",
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

    # Detects the symptom topic in the user's message, if any.
    def _detect_topic(self, message: str) -> Optional[str]:
        text = message.lower()
        for topic in self.SYMPTOM_QUESTIONS:
            if topic in text:
                return topic
        return None

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

    # Wraps a single question in a short, conversational lead-in.
    def _phrase(self, question: str, index: int) -> str:
        if index == 0:
            return (
                "I can help with that. First, so I can give you relevant "
                f"information — {question[0].lower()}{question[1:]}"
            )
        return f"Thanks. {question}"

    # Main entry point — decides whether to ask the next follow-up question.
    #
    # asked_count: how many clarification questions have already been asked in
    #              this conversation (0 if none yet).
    def check(self, message: str, asked_count: int) -> ClarificationResult:
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

        questions = self.SYMPTOM_QUESTIONS[topic]

        return ClarificationResult(
            needs_clarification=True,
            follow_up_message=self._phrase(questions[0], 0),
            topic=topic,
            next_index=1,
        )

    # Continues an in-progress clarification: asks the next question, or signals
    # that all questions are answered and it's time to retrieve an answer.
    def continue_topic(self, topic: str, asked_count: int) -> ClarificationResult:
        questions = self.SYMPTOM_QUESTIONS.get(topic, [])

        # All questions asked — stop clarifying and answer.
        if asked_count >= len(questions):
            return ClarificationResult(needs_clarification=False, topic=topic)

        return ClarificationResult(
            needs_clarification=True,
            follow_up_message=self._phrase(questions[asked_count], asked_count),
            topic=topic,
            next_index=asked_count + 1,
        )
