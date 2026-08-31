"""
Guardrails Service (Phase 2 — In Progress)
============================================
Safety layer that runs BEFORE any query reaches the LLM.

Implemented:
- Emergency detection (heart attack, suicide, overdose, chest pain)
- PII sanitization (email, phone, SSN, names)

TODO:
- More emergency patterns (choking, severe bleeding, seizure)
- Medical record number detection
- Address detection
"""

import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    """Result of safety check."""
    is_safe: bool
    sanitized_query: str
    refusal_message: Optional[str] = None
    pii_detected: bool = False
    is_emergency: bool = False


class GuardrailsService:
    """Pre-processing safety layer for user queries."""

    # Emergency patterns — detects life-threatening situations
    EMERGENCY_PATTERNS = [
        r"\b(i am|i'm|im)\s+(having|experiencing|getting)\s+(a\s+)?(heart attack|stroke|seizure)",
        r"\b(chest pain|can'?t breathe|cannot breathe)\b.*\b(right now|currently)\b",
        r"\bpain\s+in\s+(my\s+)?(heart|chest)\b",
        r"\b(overdose|overdosed|overdosing)\b",
        r"\b(suicid|kill myself|end my life|want to die)\b",
        r"\b(unconscious|not breathing|no pulse)\b",
        # TODO: Add more patterns — choking, severe bleeding, anaphylaxis
    ]

    # PII patterns — detects personal information
    PII_PATTERNS = {
        "email": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "phone": r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b[6-9]\d{9}\b",
        "ssn": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        "name_pattern": r"\b(my name is)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b",
        # TODO: Add DOB, medical record numbers, addresses
    }

    # Emergency response with India helpline numbers
    EMERGENCY_RESPONSE = (
        "EMERGENCY DETECTED\n\n"
        "It appears you may be experiencing a medical emergency.\n\n"
        "IMMEDIATELY CONTACT:\n"
        "- Emergency Services (India): 112 | Ambulance: 108\n"
        "- Emergency (US): 911 | (EU): 112\n\n"
        "This AI assistant cannot handle medical emergencies.\n"
        "Please seek immediate professional help."
    )

    # Checks query for emergencies and PII before allowing it to proceed
    def check_query(self, query: str) -> GuardrailResult:
        if self._is_emergency(query):
            return GuardrailResult(
                is_safe=False, sanitized_query=query,
                refusal_message=self.EMERGENCY_RESPONSE, is_emergency=True,
            )

        sanitized, pii_found = self._sanitize_pii(query)
        return GuardrailResult(is_safe=True, sanitized_query=sanitized, pii_detected=pii_found)

    # Matches query against emergency patterns
    def _is_emergency(self, query: str) -> bool:
        query_lower = query.lower()
        return any(re.search(p, query_lower) for p in self.EMERGENCY_PATTERNS)

    # Replaces personal data with [REDACTED] tags
    def _sanitize_pii(self, query: str) -> tuple[str, bool]:
        sanitized = query
        pii_found = False
        for pii_type, pattern in self.PII_PATTERNS.items():
            if re.findall(pattern, sanitized, re.IGNORECASE):
                pii_found = True
                sanitized = re.sub(pattern, f"[{pii_type.upper()}_REDACTED]", sanitized, flags=re.IGNORECASE)
        return sanitized, pii_found
