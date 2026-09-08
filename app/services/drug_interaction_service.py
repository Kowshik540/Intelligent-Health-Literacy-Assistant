"""
Drug Interaction Service
========================
DETERMINISTIC high-risk drug-interaction checker — pure Python, NO LLM.

A small local model cannot be trusted to reliably catch dangerous drug
combinations. This service detects medications mentioned in the text (by generic
name, common brand names, and drug class), then flags well-established high-risk
interacting pairs with a plain-language rationale and, where appropriate, a safer
alternative.

It works with the conversation's aggregated text (multi-turn memory), so a drug
the patient mentioned earlier ("I take lisinopril") is checked against a drug
they ask about later ("can I take ibuprofen?").
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# Drug classes -> list of (label, regex of generic + common brand names).
# Kept focused on the classes involved in the high-risk pairs below.
_DRUG_CLASSES: dict[str, re.Pattern] = {
    "NSAID": re.compile(
        r"\b(nsaid|ibuprofen|advil|motrin|naproxen|aleve|diclofenac|voltaren|"
        r"aspirin|ketorolac|celecoxib|celebrex|indomethacin|mefenamic)\b",
        re.IGNORECASE,
    ),
    "ACE_INHIBITOR": re.compile(
        r"\b(ace inhibitor|lisinopril|enalapril|ramipril|perindopril|captopril|"
        r"benazepril|quinapril|fosinopril|trandolapril|\w*pril)\b",
        re.IGNORECASE,
    ),
    "ARB": re.compile(
        r"\b(arb|losartan|valsartan|olmesartan|candesartan|irbesartan|"
        r"telmisartan|\w*sartan)\b",
        re.IGNORECASE,
    ),
    "ANTICOAGULANT": re.compile(
        r"\b(warfarin|coumadin|apixaban|eliquis|rivaroxaban|xarelto|"
        r"dabigatran|pradaxa|heparin|edoxaban)\b",
        re.IGNORECASE,
    ),
    "ANTIPLATELET": re.compile(
        r"\b(clopidogrel|plavix|ticagrelor|prasugrel)\b",
        re.IGNORECASE,
    ),
    "POTASSIUM_SPARING_DIURETIC": re.compile(
        r"\b(spironolactone|aldactone|eplerenone|amiloride|triamterene|"
        r"potassium supplement|potassium tablets)\b",
        re.IGNORECASE,
    ),
    "SSRI": re.compile(
        r"\b(ssri|fluoxetine|prozac|sertraline|zoloft|paroxetine|paxil|"
        r"citalopram|escitalopram|lexapro)\b",
        re.IGNORECASE,
    ),
    "TRIPTAN": re.compile(
        r"\b(triptan|sumatriptan|imitrex|rizatriptan|zolmitriptan)\b",
        re.IGNORECASE,
    ),
    "NITRATE": re.compile(
        r"\b(nitrate|nitroglycerin|nitroglycerine|isosorbide|gtn)\b",
        re.IGNORECASE,
    ),
    "PDE5_INHIBITOR": re.compile(
        r"\b(sildenafil|viagra|tadalafil|cialis|vardenafil|pde5)\b",
        re.IGNORECASE,
    ),
}


@dataclass
class DrugInteraction:
    classes: tuple[str, str]
    severity: str          # "SEVERE" | "MAJOR" | "MODERATE"
    warning: str           # plain-language rationale
    alternative: str = ""  # safer option, if any


# High-risk pairs: frozenset of two class keys -> interaction detail.
_INTERACTION_RULES: list[tuple[frozenset, DrugInteraction]] = [
    (
        frozenset({"NSAID", "ACE_INHIBITOR"}),
        DrugInteraction(
            classes=("NSAID", "ACE inhibitor"),
            severity="MAJOR",
            warning=(
                "Taking an NSAID (like ibuprofen) together with an ACE inhibitor "
                "(like lisinopril) can blunt your blood-pressure control and strain "
                "your kidneys, especially with regular use."
            ),
            alternative="For pain or fever, acetaminophen (paracetamol) is usually a safer choice — confirm with your doctor or pharmacist.",
        ),
    ),
    (
        frozenset({"NSAID", "ARB"}),
        DrugInteraction(
            classes=("NSAID", "ARB"),
            severity="MAJOR",
            warning=(
                "Combining an NSAID (like ibuprofen) with an ARB (like losartan) can "
                "reduce blood-pressure control and put extra strain on the kidneys."
            ),
            alternative="Acetaminophen (paracetamol) is usually a safer option for pain or fever — confirm with your doctor or pharmacist.",
        ),
    ),
    (
        frozenset({"NSAID", "ANTICOAGULANT"}),
        DrugInteraction(
            classes=("NSAID", "blood thinner"),
            severity="SEVERE",
            warning=(
                "Taking an NSAID (like ibuprofen or aspirin) with a blood thinner "
                "(like warfarin or apixaban) markedly raises the risk of serious "
                "bleeding, including stomach bleeding."
            ),
            alternative="For pain or fever, acetaminophen (paracetamol) is generally safer — check with your doctor first.",
        ),
    ),
    (
        frozenset({"ANTICOAGULANT", "ANTIPLATELET"}),
        DrugInteraction(
            classes=("blood thinner", "antiplatelet"),
            severity="SEVERE",
            warning=(
                "Using a blood thinner together with an antiplatelet (like clopidogrel) "
                "substantially increases bleeding risk and should only be combined under "
                "close medical supervision."
            ),
        ),
    ),
    (
        frozenset({"ACE_INHIBITOR", "POTASSIUM_SPARING_DIURETIC"}),
        DrugInteraction(
            classes=("ACE inhibitor", "potassium-sparing agent"),
            severity="MAJOR",
            warning=(
                "An ACE inhibitor with a potassium-sparing diuretic or potassium "
                "supplement can push potassium to dangerous levels (hyperkalemia), "
                "which can affect the heart rhythm."
            ),
        ),
    ),
    (
        frozenset({"ARB", "POTASSIUM_SPARING_DIURETIC"}),
        DrugInteraction(
            classes=("ARB", "potassium-sparing agent"),
            severity="MAJOR",
            warning=(
                "An ARB combined with a potassium-sparing diuretic or potassium "
                "supplement can raise potassium to dangerous levels (hyperkalemia)."
            ),
        ),
    ),
    (
        frozenset({"SSRI", "NSAID"}),
        DrugInteraction(
            classes=("SSRI", "NSAID"),
            severity="MODERATE",
            warning=(
                "An SSRI antidepressant together with an NSAID increases the risk of "
                "stomach or gastrointestinal bleeding."
            ),
            alternative="Acetaminophen (paracetamol) avoids this added bleeding risk — confirm with your clinician.",
        ),
    ),
    (
        frozenset({"SSRI", "TRIPTAN"}),
        DrugInteraction(
            classes=("SSRI", "triptan"),
            severity="MODERATE",
            warning=(
                "An SSRI with a triptan migraine medicine can, rarely, contribute to "
                "serotonin syndrome — watch for agitation, rapid heart rate, or tremor."
            ),
        ),
    ),
    (
        frozenset({"NITRATE", "PDE5_INHIBITOR"}),
        DrugInteraction(
            classes=("nitrate", "erectile-dysfunction medicine"),
            severity="SEVERE",
            warning=(
                "Nitrates (like nitroglycerin) taken with a PDE5 inhibitor (like "
                "sildenafil/Viagra) can cause a sudden, dangerous drop in blood pressure. "
                "These must not be combined."
            ),
        ),
    ),
]


@dataclass
class InteractionResult:
    detected_classes: set[str] = field(default_factory=set)
    interactions: list[DrugInteraction] = field(default_factory=list)

    @property
    def has_interaction(self) -> bool:
        return bool(self.interactions)

    def as_warning_block(self) -> str:
        """Plain-language warning block to prepend to an answer."""
        if not self.interactions:
            return ""
        # Most severe first.
        order = {"SEVERE": 0, "MAJOR": 1, "MODERATE": 2}
        items = sorted(self.interactions, key=lambda i: order.get(i.severity, 3))
        lines = ["**Medication interaction warning**"]
        for it in items:
            lines.append(f"• {it.warning}")
            if it.alternative:
                lines.append(f"  {it.alternative}")
        lines.append(
            "Do not start, stop, or combine prescription medicines without checking "
            "with your doctor or pharmacist first."
        )
        return "\n".join(lines)


class DrugInteractionService:
    """Deterministic detector of medications and high-risk interacting pairs."""

    def detect_classes(self, text: str) -> set[str]:
        found = set()
        for cls, pattern in _DRUG_CLASSES.items():
            if pattern.search(text or ""):
                found.add(cls)
        return found

    def check(self, text: str) -> InteractionResult:
        classes = self.detect_classes(text)
        result = InteractionResult(detected_classes=classes)
        if len(classes) < 2:
            return result
        for pair, detail in _INTERACTION_RULES:
            if pair.issubset(classes):
                result.interactions.append(detail)
        return result
