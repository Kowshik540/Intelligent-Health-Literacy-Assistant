"""
Clarification Service — the agentic layer of the assistant.

Instead of answering every question in a single shot, the assistant first
decides whether it has enough clinical context. If a symptom is described
without the details a clinician would normally ask for (duration, severity,
vitals, associated symptoms), the assistant asks targeted follow-up questions
before it retrieves and answers.

This turns the chatbot from a one-shot lookup into an information-gathering
agent that behaves more like a triage conversation.
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
    questions: list[str] = field(default_factory=list)


class ClarificationService:
    """Decides when to ask follow-up questions and what to ask."""

    # Each symptom maps to the follow-up questions a clinician would typically ask.
    SYMPTOM_QUESTIONS = {
        "headache": [
            "How long have you had the headache (hours, days, or weeks)?",
            "How would you rate the pain from 1 to 10?",
            "Do you know your current blood pressure reading?",
            "Any other symptoms such as fever, vision changes, or nausea?",
        ],
        "fever": [
            "What is your current temperature, if you have measured it?",
            "How many days have you had the fever?",
            "Any other symptoms such as cough, sore throat, or body aches?",
        ],
        "chest": [
            "How long have you been feeling this?",
            "Does the discomfort spread to your arm, jaw, or back?",
            "Do you know your current blood pressure reading?",
        ],
        "blood pressure": [
            "What is your most recent blood pressure reading (for example 130/80)?",
            "What is your age?",
            "Are you currently taking any blood pressure medication?",
        ],
        "cough": [
            "How long have you had the cough (days or weeks)?",
            "Is it a dry cough or are you bringing up phlegm?",
            "Do you also have a fever or difficulty breathing?",
        ],
        "stomach": [
            "Where exactly is the pain, and how long has it lasted?",
            "How severe is it from 1 to 10?",
            "Any nausea, vomiting, or change in bowel habits?",
        ],
        "diabetes": [
            "Do you know your most recent blood sugar reading?",
            "Are you currently on any diabetes medication?",
            "What is your age?",
        ],
        "pain": [
            "Where is the pain located?",
            "How long have you had it, and how severe is it from 1 to 10?",
            "Does anything make it better or worse?",
        ],
        "dizzy": [
            "How long have you been feeling dizzy?",
            "Do you know your current blood pressure reading?",
            "Any other symptoms such as headache, nausea, or fainting?",
        ],
        "tired": [
            "How long have you felt this way?",
            "Any other symptoms such as weight change, fever, or low mood?",
            "Do you know your recent blood pressure or blood sugar readings?",
        ],
    }

    # Words that suggest the message already contains clinical detail (numbers, vitals, durations).
    DETAIL_MARKERS = [
        r"\d+\s*/\s*\d+",           # blood pressure like 130/80
        r"\d+\s*(mg|ml|mmhg|bpm)",  # dosages / vitals with units
        r"\d+\s*(day|days|week|weeks|hour|hours|month|months)",  # duration
        r"\bage\b|\byears?\s*old\b|\byrs?\b",   # age given
        r"\d+\s*(degree|degrees|°|c|f)\b",      # temperature
        r"\b\d+\s*(out of|/)\s*10\b",           # pain score
    ]

    # Detects the symptom topic in the user's message, if any.
    def _detect_topic(self, message: str) -> Optional[str]:
        text = message.lower()
        for topic in self.SYMPTOM_QUESTIONS:
            if topic in text:
                return topic
        return None

    # Returns True if the message already contains enough clinical detail to skip questions.
    def _has_enough_detail(self, message: str) -> bool:
        text = message.lower()
        for pattern in self.DETAIL_MARKERS:
            if re.search(pattern, text):
                return True
        return False

    # Main entry point — decides whether to ask follow-up questions for this message.
    def check(self, message: str, already_clarified: bool) -> ClarificationResult:
        # Once we've already asked and the user replied, don't loop — go straight to answering.
        if already_clarified:
            return ClarificationResult(needs_clarification=False)

        topic = self._detect_topic(message)

        # No recognised symptom, or the user already gave detail — answer directly.
        if not topic or self._has_enough_detail(message):
            return ClarificationResult(needs_clarification=False, topic=topic)

        questions = self.SYMPTOM_QUESTIONS[topic]

        numbered = "\n".join(
            f"{i + 1}. {q}" for i, q in enumerate(questions)
        )

        follow_up = (
            "Before I share guidance from the medical documents, I need a little "
            "more information so the answer is relevant to you:\n\n"
            f"{numbered}\n\n"
            "Please share whatever you know, and I'll give you evidence-based "
            "information based on your answers."
        )

        return ClarificationResult(
            needs_clarification=True,
            follow_up_message=follow_up,
            topic=topic,
            questions=questions,
        )
