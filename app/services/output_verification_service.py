"""
Output Guardrail & Verification Service (Stage 4)
=================================================
DETERMINISTIC contradiction/acuity auditor — pure Python, NO LLM.

Runs on the generated answer BEFORE it is shown to the user. It catches the two
failure modes this architecture is designed to eliminate:

1. Numerical contradiction: the answer contradicts a rule-engine biometric
   classification — e.g. the engine said 110/60 is "Normal" but the text calls
   it "high" / "hypertension"; or the engine said a value is high but the text
   calls it "normal".

2. Acuity downplaying: triage flagged HIGH/CRITICAL acuity (e.g. an 8/10
   headache) but the answer calls it "mild", "just stress", "nothing serious",
   etc., or fails to advise prompt in-person evaluation.

If a problem is found the caller regenerates or appends a corrective safety
notice, so a hallucinated contradiction never reaches the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.services.biometric_service import BiometricResult
from app.services.clinical_triage_service import TriageResult


@dataclass
class VerificationResult:
    passed: bool
    hallucination_detected: bool
    contradiction_reason: str | None
    action: str  # "APPROVE" | "BLOCK_AND_REGENERATE"


# Categories the rule engine considers "not normal / elevated-or-worse".
_HIGH_CATEGORIES = (
    "hypertension",
    "hypertensive",
    "elevated",
    "high",
    "fever",
    "hyperpyrexia",
    "tachycardia",
    "hyperglycemia",
    "dangerous",
    "critically low",
    "hypoxemia",
)

# Words in an answer that assert a value is elevated / abnormal-high.
_SAYS_HIGH = re.compile(
    r"\b(high blood pressure|hypertension|hypertensive|elevated|too high|"
    r"dangerously high|very high|abnormally high)\b",
    re.IGNORECASE,
)
# Words in an answer that assert a value is normal / fine.
_SAYS_NORMAL = re.compile(
    r"\b(normal|healthy|within (?:the )?normal range|is fine|are fine|"
    r"nothing to worry about|no cause for concern)\b",
    re.IGNORECASE,
)

# Phrases that downplay a symptom.
_DOWNPLAY = re.compile(
    r"\b(just stress(?:ed)?|only stress|merely|just dehydrat|only dehydrat|"
    r"nothing serious|nothing to worry about|no cause for concern|"
    r"mild discomfort|just a little discomfort|probably fine|likely fine|"
    r"not (?:a )?(?:big )?(?:deal|concern|serious))\b",
    re.IGNORECASE,
)
# Phrases that appropriately urge escalation.
_URGES_CARE = re.compile(
    r"\b(emergency|call (?:112|108|911|999)|urgent|immediately|"
    r"right away|as soon as possible|seek (?:medical|professional|prompt|in-person)|"
    r"go to (?:the )?(?:er|emergency|hospital)|see a doctor|"
    r"medical attention|professional evaluation|get (?:it )?checked)\b",
    re.IGNORECASE,
)


class OutputVerificationService:
    """Deterministic auditor over the generated response."""

    def verify(
        self,
        response_text: str,
        biometrics: BiometricResult,
        triage: TriageResult,
    ) -> VerificationResult:
        text = response_text or ""
        lower = text.lower()

        # ---- Check 1: biometric numerical contradiction ------------------
        for reading in biometrics.readings:
            category = reading.category.lower()
            is_high_category = any(k in category for k in _HIGH_CATEGORIES)
            is_normal_category = category.startswith("normal")

            # Only inspect the sentence(s) that actually mention this reading's
            # numbers, so an unrelated "normal" elsewhere doesn't trip us.
            mentions = self._mentions_value(text, reading.raw)

            if is_normal_category and mentions and _SAYS_HIGH.search(mentions):
                return VerificationResult(
                    passed=False,
                    hallucination_detected=True,
                    contradiction_reason=(
                        f"Rule engine classified {reading.raw} as '{reading.category}', "
                        f"but the answer describes it as high/abnormal."
                    ),
                    action="BLOCK_AND_REGENERATE",
                )

            if is_high_category and mentions and _SAYS_NORMAL.search(mentions) \
                    and not _SAYS_HIGH.search(mentions):
                return VerificationResult(
                    passed=False,
                    hallucination_detected=True,
                    contradiction_reason=(
                        f"Rule engine classified {reading.raw} as '{reading.category}', "
                        f"but the answer describes it as normal/fine."
                    ),
                    action="BLOCK_AND_REGENERATE",
                )

        # ---- Check 2: acuity downplaying ---------------------------------
        if triage.acuity_level in ("HIGH", "CRITICAL"):
            if _DOWNPLAY.search(lower):
                return VerificationResult(
                    passed=False,
                    hallucination_detected=True,
                    contradiction_reason=(
                        f"Triage acuity is {triage.acuity_level} but the answer "
                        f"downplays the symptom."
                    ),
                    action="BLOCK_AND_REGENERATE",
                )
            if not _URGES_CARE.search(lower):
                return VerificationResult(
                    passed=False,
                    hallucination_detected=False,
                    contradiction_reason=(
                        f"Triage acuity is {triage.acuity_level} but the answer "
                        f"does not advise prompt in-person medical evaluation."
                    ),
                    action="BLOCK_AND_REGENERATE",
                )

        return VerificationResult(
            passed=True,
            hallucination_detected=False,
            contradiction_reason=None,
            action="APPROVE",
        )

    @staticmethod
    def _mentions_value(text: str, raw: str) -> str:
        """
        Return the sentence(s) containing this reading's raw value (e.g. "110/60"
        or "101°F"). Falls back to the full text if the raw value has no easily
        matchable numeric core, so we still catch contradictions.
        """
        # Extract a numeric core to search for (handles "110/60", "101°F", "88%").
        core = re.search(r"\d{1,3}(?:\s*/\s*\d{1,3})?", raw)
        needle = core.group(0).replace(" ", "") if core else None

        sentences = re.split(r"(?<=[.!?])\s+", text)
        if not needle:
            return text
        hits = [s for s in sentences if needle in s.replace(" ", "")]
        return " ".join(hits) if hits else ""
