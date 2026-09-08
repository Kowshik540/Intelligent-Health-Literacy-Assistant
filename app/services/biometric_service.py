"""
Parses vital signs from free text (BP, temperature, HR, SpO2, glucose) and
classifies them against fixed clinical thresholds.

Done in code, not the LLM: a model used as a calculator will happily call
110/60 "hypertension". The classifications feed the generation prompt, and
critical readings (e.g. hypertensive crisis, SpO2 < 90) raise the triage acuity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class BiometricReading:
    kind: str            # "blood_pressure" | "temperature" | ...
    raw: str             # what was matched in the text, e.g. "110/60"
    category: str        # deterministic label, e.g. "Normal"
    detail: str          # human sentence, e.g. "Blood pressure 110/60 mmHg is Normal."
    is_critical: bool = False


@dataclass
class BiometricResult:
    readings: list[BiometricReading] = field(default_factory=list)
    critical_flags: list[str] = field(default_factory=list)

    @property
    def found_any(self) -> bool:
        return bool(self.readings)

    def as_prompt_context(self) -> str:
        """Deterministic classifications for injection into the LLM prompt."""
        if not self.readings:
            return "Vital signs: none provided."
        lines = [f"- {r.detail}" for r in self.readings]
        return "Confirmed vital-sign findings (authoritative; state as-is):\n" + "\n".join(lines)


class BiometricService:
    """Extracts and classifies vital signs with deterministic rules (no LLM)."""

    # Blood pressure: "110/60", "120 / 80", optionally "mmHg". Guard against
    # matching dates/fractions by requiring plausible ranges after parsing.
    _BP = re.compile(r"\b(\d{2,3})\s*/\s*(\d{2,3})\b(?:\s*mm\s*hg)?", re.IGNORECASE)

    # Temperature: "101.5 F", "38.5 C", "temp 99". Capture unit if present.
    _TEMP = re.compile(
        r"\b(\d{2,3}(?:\.\d)?)\s*(?:°|deg(?:rees)?)?\s*(f|c|fahrenheit|celsius)\b",
        re.IGNORECASE,
    )
    _TEMP_LABELLED = re.compile(
        r"\b(?:temp(?:erature)?)\s*(?:is|:|of)?\s*(\d{2,3}(?:\.\d)?)\b",
        re.IGNORECASE,
    )

    # Heart rate / pulse: "HR 110", "pulse of 48 bpm", "heart rate is 72".
    _HR = re.compile(
        r"\b(?:hr|heart rate|pulse)\s*(?:is|:|of)?\s*(\d{2,3})\s*(?:bpm)?\b",
        re.IGNORECASE,
    )

    # SpO2 / oxygen saturation: "spo2 88", "oxygen saturation 92%", "o2 sat 95",
    # "oxygen saturation was 88 percent". Allow a few filler words between the
    # keyword and the number.
    _SPO2 = re.compile(
        r"\b(?:spo2|o2 sat(?:uration)?|oxygen sat(?:uration)?|sat(?:uration)?s?)\b"
        r"[^\d\n]{0,20}?"          # a short run of words (no digits) may sit between
        r"(\d{2,3})\s*(?:%|percent)?\b",
        re.IGNORECASE,
    )

    # Blood glucose: "sugar 250", "glucose of 90 mg/dl", "blood sugar is 60".
    _GLUCOSE = re.compile(
        r"\b(?:blood sugar|glucose|sugar level|sugar)\s*(?:is|:|of|level)?\s*(\d{2,3})\s*(?:mg/?dl)?\b",
        re.IGNORECASE,
    )

    def evaluate(self, message: str) -> BiometricResult:
        text = message or ""
        result = BiometricResult()

        self._eval_bp(text, result)
        self._eval_temperature(text, result)
        self._eval_heart_rate(text, result)
        self._eval_spo2(text, result)
        self._eval_glucose(text, result)

        return result

    # ---- Blood pressure (ACC/AHA 2017 categories) -------------------------
    def _eval_bp(self, text: str, result: BiometricResult) -> None:
        for m in self._BP.finditer(text):
            systolic = int(m.group(1))
            diastolic = int(m.group(2))
            # Plausibility guard: skip implausible pairs (dates, ratios).
            if not (60 <= systolic <= 300 and 30 <= diastolic <= 200):
                continue
            if diastolic >= systolic:
                continue

            category, critical = self._classify_bp(systolic, diastolic)
            detail = (
                f"Blood pressure {systolic}/{diastolic} mmHg is classified as {category}."
            )
            result.readings.append(
                BiometricReading(
                    kind="blood_pressure",
                    raw=f"{systolic}/{diastolic}",
                    category=category,
                    detail=detail,
                    is_critical=critical,
                )
            )
            if critical:
                result.critical_flags.append(
                    f"Hypertensive crisis ({systolic}/{diastolic} mmHg)"
                )

    @staticmethod
    def _classify_bp(systolic: int, diastolic: int) -> tuple[str, bool]:
        # Hypertensive crisis takes precedence.
        if systolic > 180 or diastolic > 120:
            return "Hypertensive Crisis (seek emergency care)", True
        if systolic < 90 or diastolic < 60:
            return "Low (Hypotension)", False
        if systolic >= 140 or diastolic >= 90:
            return "Stage 2 Hypertension", False
        if systolic >= 130 or diastolic >= 80:
            return "Stage 1 Hypertension", False
        if 120 <= systolic <= 129 and diastolic < 80:
            return "Elevated", False
        if systolic < 120 and diastolic < 80:
            return "Normal", False
        # Fallback for any uncovered combination.
        return "Indeterminate", False

    # ---- Temperature ------------------------------------------------------
    def _eval_temperature(self, text: str, result: BiometricResult) -> None:
        handled_values: set[float] = set()

        for m in self._TEMP.finditer(text):
            value = float(m.group(1))
            unit = m.group(2).lower()[0]  # 'f' or 'c'
            self._add_temperature(value, unit, result, handled_values)

        # Labelled but unit-less temperatures: infer unit from magnitude.
        for m in self._TEMP_LABELLED.finditer(text):
            value = float(m.group(1))
            if value in handled_values:
                continue
            unit = "f" if value >= 90 else "c"
            self._add_temperature(value, unit, result, handled_values)

    def _add_temperature(self, value, unit, result, handled_values) -> None:
        # Normalise to Fahrenheit for classification.
        if unit == "c":
            if not (30.0 <= value <= 45.0):
                return
            fahrenheit = value * 9 / 5 + 32
            shown = f"{value:g}°C"
        else:
            if not (90.0 <= value <= 115.0):
                return
            fahrenheit = value
            shown = f"{value:g}°F"

        handled_values.add(value)
        category, critical = self._classify_temp(fahrenheit)
        detail = f"Body temperature {shown} is classified as {category}."
        result.readings.append(
            BiometricReading(
                kind="temperature",
                raw=shown,
                category=category,
                detail=detail,
                is_critical=critical,
            )
        )
        if critical:
            result.critical_flags.append(f"Hyperpyrexia ({shown})")

    @staticmethod
    def _classify_temp(fahrenheit: float) -> tuple[str, bool]:
        if fahrenheit >= 104.0:
            return "Very High Fever (hyperpyrexia)", True
        if fahrenheit >= 100.4:
            return "Fever", False
        if fahrenheit >= 99.1:
            return "Low-grade (slightly elevated)", False
        if fahrenheit < 95.0:
            return "Low (hypothermia)", True
        return "Normal", False

    # ---- Heart rate -------------------------------------------------------
    def _eval_heart_rate(self, text: str, result: BiometricResult) -> None:
        for m in self._HR.finditer(text):
            bpm = int(m.group(1))
            if not (25 <= bpm <= 300):
                continue
            category, critical = self._classify_hr(bpm)
            detail = f"Heart rate {bpm} bpm is classified as {category}."
            result.readings.append(
                BiometricReading(
                    kind="heart_rate",
                    raw=str(bpm),
                    category=category,
                    detail=detail,
                    is_critical=critical,
                )
            )
            if critical:
                result.critical_flags.append(f"Extreme heart rate ({bpm} bpm)")

    @staticmethod
    def _classify_hr(bpm: int) -> tuple[str, bool]:
        if bpm >= 130 or bpm <= 40:
            return ("Markedly abnormal", True)
        if bpm > 100:
            return ("Elevated (tachycardia)", False)
        if bpm < 60:
            return ("Low (bradycardia)", False)
        return ("Normal", False)

    # ---- SpO2 -------------------------------------------------------------
    def _eval_spo2(self, text: str, result: BiometricResult) -> None:
        for m in self._SPO2.finditer(text):
            spo2 = int(m.group(1))
            if not (50 <= spo2 <= 100):
                continue
            category, critical = self._classify_spo2(spo2)
            detail = f"Oxygen saturation {spo2}% is classified as {category}."
            result.readings.append(
                BiometricReading(
                    kind="spo2",
                    raw=f"{spo2}%",
                    category=category,
                    detail=detail,
                    is_critical=critical,
                )
            )
            if critical:
                result.critical_flags.append(f"Low oxygen saturation ({spo2}%)")

    @staticmethod
    def _classify_spo2(spo2: int) -> tuple[str, bool]:
        if spo2 < 90:
            return ("Critically Low (hypoxemia)", True)
        if spo2 < 95:
            return ("Low", False)
        return ("Normal", False)

    # ---- Blood glucose ----------------------------------------------------
    def _eval_glucose(self, text: str, result: BiometricResult) -> None:
        for m in self._GLUCOSE.finditer(text):
            mgdl = int(m.group(1))
            if not (20 <= mgdl <= 800):
                continue
            category, critical = self._classify_glucose(mgdl)
            detail = f"Blood glucose {mgdl} mg/dL is classified as {category}."
            result.readings.append(
                BiometricReading(
                    kind="glucose",
                    raw=str(mgdl),
                    category=category,
                    detail=detail,
                    is_critical=critical,
                )
            )
            if critical:
                result.critical_flags.append(f"Dangerous blood glucose ({mgdl} mg/dL)")

    @staticmethod
    def _classify_glucose(mgdl: int) -> tuple[str, bool]:
        if mgdl < 54 or mgdl >= 300:
            return ("Dangerous level", True)
        if mgdl < 70:
            return ("Low (hypoglycemia)", False)
        if mgdl >= 126:
            return ("High (hyperglycemia range)", False)
        if mgdl >= 100:
            return ("Elevated (prediabetic fasting range)", False)
        return ("Normal (fasting range)", False)
