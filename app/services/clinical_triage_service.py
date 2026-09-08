"""
Clinical Triage & Red-Flag Service (Stage 1)
============================================
DETERMINISTIC acuity classifier — pure Python, NO LLM.

Why deterministic?
------------------
Triage decisions must be predictable and auditable. A small local LLM should
never be trusted to decide whether an 8/10 headache is an emergency. This
service uses explicit rules to detect red-flag symptoms and assign an acuity
level, so the gatekeeping logic is reproducible and cannot "hallucinate".

It runs BEFORE retrieval/generation. Its output (acuity + red flags) is fed
into the RAG synthesizer prompt so the LLM cannot downplay a serious symptom,
and into the output verifier so a downplayed answer is blocked.

Acuity levels
-------------
CRITICAL  — life-threatening pattern (thunderclap + neuro, stroke signs,
            meningeal signs with fever). Should bypass general RAG.
HIGH      — severe pain (>= 7/10) or an isolated red flag. Needs prompt
            in-person evaluation.
MODERATE  — notable but non-emergency symptoms.
LOW       — general/informational query, no red flags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class TriageResult:
    acuity_level: str = "LOW"  # CRITICAL | HIGH | MODERATE | LOW
    red_flag_detected: bool = False
    flagged_symptoms: list[str] = field(default_factory=list)
    requires_immediate_escalation: bool = False

    def as_prompt_context(self) -> str:
        """Compact human-readable summary for injection into the LLM prompt."""
        if not self.red_flag_detected and self.acuity_level == "LOW":
            return "Triage Acuity: LOW (no red-flag symptoms detected)."
        flags = ", ".join(self.flagged_symptoms) if self.flagged_symptoms else "none"
        return (
            f"Triage Acuity: {self.acuity_level}. "
            f"Red-flag symptoms detected: {flags}. "
            f"Immediate escalation required: {self.requires_immediate_escalation}."
        )


class ClinicalTriageService:
    """Rule-based red-flag detector and acuity classifier (no LLM)."""

    # --- Pain severity -----------------------------------------------------
    # Explicit numeric scale "8/10", "9 out of 10", etc.
    _PAIN_SCALE = re.compile(
        r"\b(\d{1,2})\s*(?:/|out of)\s*10\b", re.IGNORECASE
    )
    # Qualitative severe-pain language.
    _SEVERE_WORDS = re.compile(
        r"\b(worst (?:pain|headache) (?:ever|of my life)|"
        r"unbearable|excruciating|severe(?:ly)?|agoniz|"
        r"most painful|10/10)\b",
        re.IGNORECASE,
    )

    # --- Thunderclap / sudden onset ---------------------------------------
    _THUNDERCLAP = re.compile(
        r"\b(thunderclap|"
        r"sudden(?:ly)?\b.{0,25}\b(?:severe|worst|headache)|"
        r"came on (?:suddenly|in seconds)|peaked in (?:seconds|minutes)|"
        r"hit me (?:suddenly|out of nowhere))\b",
        re.IGNORECASE,
    )

    # "Worst headache of my life / worst ever" — a classic red flag for
    # subarachnoid haemorrhage on its own, regardless of stated onset speed.
    _WORST_HEADACHE = re.compile(
        r"\bworst (?:headache|head\s*ache) (?:of my life|ever|i(?:'ve| have) (?:ever )?had)\b",
        re.IGNORECASE,
    )

    # --- Cardiovascular red flags (possible ACS / MI) ---------------------
    _CARDIAC = re.compile(
        r"\b(chest (?:pain|pressure|tightness|discomfort|heaviness)|"
        r"heart (?:pain|pressure|attack)|(?:pain|hurt\w*|ache\w*|pressure|tightness) "
        r"(?:in|on|around|near) (?:my |the )?(?:heart|chest)|"
        r"crushing (?:pain|chest)|pressure (?:in|on) (?:my )?chest|"
        r"my heart (?:hurts|is hurting|aches)|"
        r"(?:pain|tightness) (?:radiat|spreading|going) (?:to|down|into) (?:my )?(?:left )?(?:arm|jaw|back|shoulder)|"
        r"(?:left )?arm and (?:jaw|chest)|heart attack)\b",
        re.IGNORECASE,
    )
    _DIAPHORESIS = re.compile(
        r"\b(sweating|diaphore|cold sweat|breaking out in a sweat|clammy)\b",
        re.IGNORECASE,
    )
    _SYNCOPE = re.compile(
        r"\b(faint(?:ing|ed)?|passed out|about to pass out|blacked out|syncope|lost consciousness)\b",
        re.IGNORECASE,
    )

    # --- Respiratory red flags --------------------------------------------
    # Per the zero-question emergency protocol, any real breathing difficulty
    # (including plain "shortness of breath" / "difficulty breathing") is an
    # escalating red flag — so distress and dyspnea are treated together.
    _RESP_DISTRESS = re.compile(
        r"\b(can'?t breathe|cannot breathe|can'?t catch my breath|"
        r"struggling to breathe|severe (?:shortness of breath|dyspnea)|"
        r"suffocat\w*|can'?t get (?:enough )?air|not getting (?:enough )?air|"
        r"gasping|stridor|turning blue|blue lips|cyanosis|choking|"
        r"shortness of breath|short of breath|difficulty breathing|"
        r"trouble breathing|hard to breathe|breathless|"
        r"can'?t (?:speak|talk) in (?:full )?sentences)\b",
        re.IGNORECASE,
    )
    _DYSPNEA = re.compile(
        r"\b(shortness of breath|short of breath|out of breath|"
        r"difficulty breathing|trouble breathing|breathless)\b",
        re.IGNORECASE,
    )

    # --- Surgical abdomen -------------------------------------------------
    _ACUTE_ABDOMEN = re.compile(
        r"\b(rigid (?:abdomen|belly|stomach)|board.?like|"
        r"rebound tenderness|(?:severe|sudden) (?:abdominal|belly|stomach) pain)\b",
        re.IGNORECASE,
    )
    # Any mention of the abdominal region (for combination rules like
    # abdominal pain + vomiting, or abdominal pain >= 7/10).
    _ABDOMEN_REGION = re.compile(
        r"\b(abdomen|abdominal|stomach|belly|tummy|"
        r"(?:lower|upper|right|left)\s+(?:right|left)?\s*(?:quadrant|abdomen|belly|side)|"
        r"rlq|llq|ruq|luq|appendix|pelvic)\b",
        re.IGNORECASE,
    )
    # Vomiting / nausea.
    _VOMITING = re.compile(
        r"\b(vomit(?:ing|ed)?|throwing up|threw up|nause(?:a|ous|ated)|being sick|puking)\b",
        re.IGNORECASE,
    )
    # Blood in vomit — GI bleed red flag.
    _HEMATEMESIS = re.compile(
        r"\b(vomit(?:ing)? blood|blood in (?:my )?vomit|coffee[- ]ground|throwing up blood)\b",
        re.IGNORECASE,
    )

    # --- Sepsis / meningitis extras ---------------------------------------
    _PETECHIAL = re.compile(
        r"\b(non.?blanching rash|petechia|purpuric rash|rash that (?:doesn'?t|does not) fade)\b",
        re.IGNORECASE,
    )

    # --- Neurological deficits --------------------------------------------
    _NEURO = re.compile(
        r"\b(facial droop|face (?:is )?drooping|slurred speech|"
        r"can'?t speak|difficulty speaking|trouble speaking|"
        r"weakness on one side|one[- ]sided weakness|"
        r"numbness on one side|can'?t move (?:my )?(?:arm|leg|face)|"
        r"vision (?:loss|changes)|(?:double|blurred) vision|"
        r"sudden confusion|can'?t understand|loss of balance|"
        r"unable to walk)\b",
        re.IGNORECASE,
    )

    # --- Meningeal signs ---------------------------------------------------
    _STIFF_NECK = re.compile(r"\b(stiff neck|neck stiffness|can'?t move my neck)\b", re.IGNORECASE)
    _FEVER = re.compile(r"\b(fever|high temperature|feverish|103|104|105)\b", re.IGNORECASE)
    _PHOTOPHOBIA = re.compile(r"\b(sensitiv\w* to light|light hurts|photophobia)\b", re.IGNORECASE)

    # Any mention of a headache (for combination rules like headache + fever).
    _HEADACHE = re.compile(r"\b(head\s*ache|migraine|head hurts|head pain|pain in my head)\b", re.IGNORECASE)
    # Altered mental status / lethargy (sepsis / CNS red flag with fever).
    _ALTERED = re.compile(
        r"\b(confus(?:ed|ion)|disorient|very drowsy|extremely (?:sleepy|drowsy)|"
        r"lethargic|unresponsive|hard to wake|can'?t stay awake)\b",
        re.IGNORECASE,
    )

    def assess(self, message: str) -> TriageResult:
        text = message or ""
        flags: list[str] = []

        # ---- Pain acuity --------------------------------------------------
        severe_pain = False
        pain_score = self._max_pain_score(text)
        if pain_score is not None and pain_score >= 7:
            severe_pain = True
            flags.append(f"severe pain ({pain_score}/10)")
        elif self._SEVERE_WORDS.search(text):
            severe_pain = True
            flags.append("severe pain (described qualitatively)")

        # ---- Individual red flags ----------------------------------------
        worst_headache = bool(self._WORST_HEADACHE.search(text))
        thunderclap = bool(self._THUNDERCLAP.search(text)) or worst_headache
        if thunderclap:
            flags.append("thunderclap / sudden-onset or worst-ever headache")

        neuro = bool(self._NEURO.search(text))
        if neuro:
            flags.append("neurological deficit (possible stroke sign)")

        stiff_neck = bool(self._STIFF_NECK.search(text))
        fever = bool(self._FEVER.search(text))
        photophobia = bool(self._PHOTOPHOBIA.search(text))
        meningeal = stiff_neck and (fever or photophobia)
        if meningeal:
            flags.append("meningeal signs (stiff neck with fever/photophobia)")

        # Cardiovascular: chest pain / radiation, especially with diaphoresis
        # or dyspnea (possible acute coronary syndrome).
        cardiac = bool(self._CARDIAC.search(text))
        diaphoresis = bool(self._DIAPHORESIS.search(text))
        syncope = bool(self._SYNCOPE.search(text))
        if cardiac:
            flags.append("chest pain / cardiac red flag (possible heart attack)")
        if syncope:
            flags.append("syncope / loss of consciousness")

        # Respiratory distress.
        resp_distress = bool(self._RESP_DISTRESS.search(text))
        dyspnea = bool(self._DYSPNEA.search(text))
        if resp_distress:
            flags.append("severe respiratory distress")

        # Abdominal presentations. An acute abdomen can be limb- and
        # life-threatening (appendicitis, perforation, obstruction), so we
        # escalate severe abdominal pain and abdominal pain with vomiting.
        abdomen_region = bool(self._ABDOMEN_REGION.search(text))
        vomiting = bool(self._VOMITING.search(text))
        hematemesis = bool(self._HEMATEMESIS.search(text))

        explicit_acute_abdomen = bool(self._ACUTE_ABDOMEN.search(text))
        severe_abdominal = abdomen_region and severe_pain          # pain >= 7/10 in the abdomen
        abdominal_with_vomiting = abdomen_region and vomiting      # any abdominal pain + vomiting

        acute_abdomen = (
            explicit_acute_abdomen
            or severe_abdominal
            or abdominal_with_vomiting
        )
        if acute_abdomen:
            flags.append("acute abdomen (possible surgical emergency)")
        if hematemesis:
            flags.append("vomiting blood / coffee-ground emesis (GI bleed)")

        petechial = bool(self._PETECHIAL.search(text))
        if petechial and fever:
            flags.append("non-blanching rash with fever (possible sepsis/meningococcemia)")

        headache = bool(self._HEADACHE.search(text))
        altered = bool(self._ALTERED.search(text))

        # ---- COMBINATION RED FLAGS (clinical rule-outs) ------------------
        # These pairings are dangerous even when neither element alone is
        # CRITICAL, so they are evaluated explicitly.

        # Headache + fever => suspected CNS infection (meningitis/encephalitis).
        # This is the classic miss: a moderate/severe headache with fever must
        # NOT be treated as a benign tension headache.
        meningitis_risk = headache and fever
        if meningitis_risk:
            flags.append("headache with fever (possible meningitis / CNS infection)")

        # Fever + altered mental status / confusion => possible sepsis or
        # CNS infection.
        fever_altered = fever and altered
        if fever_altered:
            flags.append("fever with confusion/altered mental status (possible sepsis/CNS infection)")

        # Fever + neurological deficit.
        fever_neuro = fever and neuro
        if fever_neuro:
            flags.append("fever with neurological signs (possible CNS infection)")

        red_flag = bool(flags)

        # ---- Acuity determination ----------------------------------------
        # ZERO-QUESTION EMERGENCY PROTOCOL: any severe pain (>= 7/10 or clearly
        # severe) is an absolute escalation trigger on its own — the assistant
        # must issue an emergency directive WITHOUT asking any clarifying
        # question. So severe pain alone is CRITICAL, not merely HIGH.
        critical = (
            neuro
            or meningeal
            or resp_distress        # includes plain shortness of breath / suffocating
            or syncope
            or cardiac              # any chest / heart red flag escalates
            or worst_headache       # "worst headache of my life" = red flag
            or severe_pain          # pain >= 7/10 anywhere => zero-question emergency
            or (thunderclap and severe_pain)
            or (petechial and fever)
            or acute_abdomen        # severe abdominal pain, or abdominal pain + vomiting
            or hematemesis          # vomiting blood
            or meningitis_risk      # headache + fever = CNS-infection rule-out
            or fever_altered        # fever + confusion = sepsis/CNS rule-out
            or fever_neuro          # fever + focal deficit
        )

        if critical:
            acuity = "CRITICAL"
        elif severe_pain or thunderclap or dyspnea or diaphoresis:
            acuity = "HIGH"
        elif red_flag:
            acuity = "MODERATE"
        else:
            acuity = "LOW"

        return TriageResult(
            acuity_level=acuity,
            red_flag_detected=red_flag,
            flagged_symptoms=flags,
            requires_immediate_escalation=critical,
        )

    # ----------------------------------------------------------------------
    def _max_pain_score(self, text: str) -> int | None:
        """Highest valid pain-scale value found in the text (0..10)."""
        best: int | None = None
        for m in self._PAIN_SCALE.finditer(text):
            try:
                val = int(m.group(1))
            except ValueError:
                continue
            if 0 <= val <= 10:
                best = val if best is None else max(best, val)
        return best
