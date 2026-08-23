"""
Guardrails Service — Safety layer that runs BEFORE any query reaches the LLM.
Handles two critical safety functions:
1. Emergency Detection: Identifies life-threatening situations and redirects to 112/108
2. PII Sanitization: Removes personal data (email, phone, SSN) before processing
"""

import re
from typing import Optional
from dataclasses import dataclass


@dataclass
class GuardrailResult:
    """Result of the guardrails check — determines if the query is safe to process."""
    is_safe: bool
    sanitized_query: str
    refusal_message: Optional[str] = None
    pii_detected: bool = False
    is_emergency: bool = False


class GuardrailsService:
    """Pre-processing safety layer for all incoming user queries."""

    # Regex patterns that indicate a medical emergency requiring immediate help
    EMERGENCY_PATTERNS = [
        r"\b(i am|i'm|im)\s+(having|experiencing|getting)\s+(a\s+)?(heart attack|stroke|seizure|anaphylaxis|anaphylactic)",
        r"\b(chest pain|can'?t breathe|cannot breathe|difficulty breathing)\b.*\b(right now|currently|at this moment)\b",
        r"\b(i\s+(am\s+)?(having|feeling|getting|experiencing)|i\s+have|i'?m\s+(having|getting|feeling))\b.{0,30}\b(pain|ache|pressure|tightness|heavy)\b.{0,15}\b(heart|chest|left chest)\b",
        r"\bpain\s+in\s+(my\s+)?(heart|chest)\b",
        r"\b(overdose|overdosed|overdosing)\b",
        r"\b(suicid|kill myself|end my life|want to die|self.?harm)\b",
        r"\b(choking|can'?t swallow|throat closing)\b.*\b(right now|help|emergency)\b",
        r"\b(severe bleeding|won'?t stop bleeding|blood everywhere)\b",
        r"\b(unconscious|passed out|not breathing|no pulse)\b",
        r"\b(call 911|need ambulance|emergency room|ER now)\b",
    ]

    # Regex patterns for detecting personally identifiable information
    PII_PATTERNS = {
        "email": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "phone": r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b[6-9]\d{9}\b",
        "ssn": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        "date_of_birth": r"\b(dob|date of birth|born on)[\s:]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "medical_record_number": r"\b(mrn|medical record|patient id)[\s:#]*[a-zA-Z0-9-]+\b",
        "address": r"\b\d{1,5}\s+[a-zA-Z0-9\s,.]+\b(street|st|avenue|ave|road|rd|drive|dr|lane|ln|blvd|boulevard)\b",
        "name_pattern": r"\b(my name is)\s+[A-Z][a-z]+\s+[A-Z][a-z]+\b",
    }

    # Emergency response message with India + international helpline numbers
    EMERGENCY_RESPONSE = (
        "🚨 EMERGENCY DETECTED 🚨\n\n"
        "Based on your message, it appears you may be experiencing a medical emergency.\n\n"
        "IMMEDIATELY CONTACT:\n"
        "• Emergency Services (India): 112 (all emergencies) | 108 (ambulance)\n"
        "• iCall Mental Health Helpline (India): 9152987821\n"
        "• Vandrevala Foundation (24x7): 1860-2662-345\n"
        "• Poison Control (US): 1-800-222-1222\n"
        "• Emergency Services (US): 911 | (EU): 112 | (UK): 999\n\n"
        "This AI assistant is NOT equipped to handle medical emergencies. "
        "Please seek immediate professional medical help.\n\n"
        "Do NOT rely on any AI system for emergency medical situations."
    )

    # Main entry point — checks the query for emergencies and PII before allowing it through
    def check_query(self, query: str) -> GuardrailResult:
        if self._is_emergency_query(query):
            return GuardrailResult(
                is_safe=False,
                sanitized_query=query,
                refusal_message=self.EMERGENCY_RESPONSE,
                is_emergency=True,
            )

        sanitized_query, pii_found = self._sanitize_pii(query)

        return GuardrailResult(
            is_safe=True,
            sanitized_query=sanitized_query,
            pii_detected=pii_found,
        )

    # Checks if the query matches any emergency pattern (heart attack, suicide, overdose, etc.)
    def _is_emergency_query(self, query: str) -> bool:
        query_lower = query.lower()
        for pattern in self.EMERGENCY_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        return False

    # Scans for PII and replaces it with [REDACTED] tags so personal data never reaches the LLM
    def _sanitize_pii(self, query: str) -> tuple[str, bool]:
        sanitized = query
        pii_found = False

        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, sanitized, re.IGNORECASE)
            if matches:
                pii_found = True
                sanitized = re.sub(
                    pattern, f"[{pii_type.upper()}_REDACTED]", sanitized, flags=re.IGNORECASE
                )

        return sanitized, pii_found
