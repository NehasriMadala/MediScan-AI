from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LabValue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    test_name: str
    value: float | None = None
    unit: str = ""
    reference_range: str = ""
    status: Literal["Low", "Normal", "High", "Critical", "Unknown"] = "Unknown"
    page_number: int = 1
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    original_text: str = ""
    reported_flag: str = ""
    verification_needed: bool = False


TEST_ALIASES = {
    "hemoglobin": ("Hemoglobin", r"(?:haemoglobin|hemoglobin|\bhb\b)"),
    "rbc": ("RBC Count", r"(?:rbc(?: count)?|red blood cells?|erythrocytes?)"),
    "wbc": ("WBC Count", r"(?:wbc(?: count)?|white blood cells?|leukocytes?)"),
    "platelets": ("Platelet Count", r"(?:platelets?|platelet count)"),
    "hematocrit": ("Hematocrit", r"(?:hematocrit|haematocrit|hct|pcv)"),
    "mcv": ("MCV", r"(?:mean corpuscular volume|\bmcv\b)"),
    "mch": ("MCH", r"(?:mean corpuscular hemoglobin|\bmch\b)"),
    "mchc": ("MCHC", r"(?:mean corpuscular hemoglobin concentration|\bmchc\b)"),
    "neutrophils": ("Neutrophils", r"(?:neutrophils?|neutrophil count)"),
    "lymphocytes": ("Lymphocytes", r"(?:lymphocytes?|lymphocyte count)"),
    "glucose": ("Blood Glucose", r"(?:blood glucose|fasting blood sugar|fasting glucose|\bfbs\b|glucose)"),
    "hba1c": ("HbA1c", r"(?:hba1c|glycated hemoglobin|glycohemoglobin)"),
    "cholesterol": ("Total Cholesterol", r"(?:total cholesterol|cholesterol total)"),
    "hdl": ("HDL", r"(?:hdl(?: cholesterol)?|hdl-c)"),
    "ldl": ("LDL", r"(?:ldl(?: cholesterol)?|ldl-c)"),
    "triglycerides": ("Triglycerides", r"triglycerides?"),
    "creatinine": ("Creatinine", r"creatinine"),
    "urea": ("Urea", r"(?:urea|blood urea nitrogen|bun)"),
    "uric_acid": ("Uric Acid", r"(?:uric acid|urate)"),
    "ast": ("SGOT/AST", r"(?:sgot|ast|aspartate aminotransferase)"),
    "alt": ("SGPT/ALT", r"(?:sgpt|alt|alanine aminotransferase)"),
    "bilirubin": ("Bilirubin", r"(?:total bilirubin|bilirubin total|bilirubin)"),
    "tsh": ("TSH", r"(?:thyroid stimulating hormone|tsh)"),
    "b12": ("Vitamin B12", r"(?:vitamin b12|vit b12|b12)"),
    "vitamin_d": ("Vitamin D", r"(?:vitamin d|25-oh vitamin d|25-oh d)"),
    "calcium": ("Calcium", r"(?:serum calcium|calcium|ca)"),
    "sodium": ("Sodium", r"(?:serum sodium|sodium|\bna\b)"),
    "potassium": ("Potassium", r"(?:serum potassium|potassium|\bk\b)"),
    "esr": ("ESR", r"(?:esr|erythrocyte sedimentation rate)"),
}

NUMBER = r"[-+]?\d+(?:[.,]\d+)?"
UNIT_PATTERN = r"(?:million|cells|µL|uL|fL|pg|mIU|µIU|mg|g|mL|dL|L|mmol|mol|IU|U|%)[A-Za-zµµ^*/.0-9³²_-]*"


def parse_number(text: str) -> float | None:
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def parse_reference(text: str) -> str:
    patterns = [
        r"(?:([<>]=?|\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*([A-Za-zµ/%^.\d /]*))",
        r"(?:([<>]=?\s*\d+(?:\.\d+)?))",
        r"(?:\b(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?))",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = " ".join(part.strip() for part in match.groups() if part).strip()
            return value
    return ""


def classify_status(value: float | None, reference_range: str, laboratory_status: str = "") -> str:
    if laboratory_status:
        normalized = laboratory_status.strip().lower()
        if normalized in {"high", "h", "positive", "abnormal high", "above"}:
            return "High"
        if normalized in {"low", "l", "abnormal low", "below"}:
            return "Low"
        if normalized in {"normal", "n", "negative"}:
            return "Normal"
    if value is None:
        return "Unknown"

    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)", reference_range)
    if match:
        lower, upper = map(float, match.groups())
        if value < lower:
            return "Low"
        if value > upper:
            return "High"
        return "Normal"

    below = re.search(r"<[=]?\s*(\d+(?:\.\d+)?)", reference_range)
    above = re.search(r">[=]?\s*(\d+(?:\.\d+)?)", reference_range)
    if below:
        return "Normal" if value < float(below.group(1)) else "High"
    if above:
        return "Normal" if value > float(above.group(1)) else "Low"
    return "Unknown"


def _extract_table_blocks(text: str, ocr_confidence: float, page_number: int) -> list[LabValue]:
    results: list[LabValue] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for line_index, line in enumerate(lines):
        matched_name: tuple[str, str] | None = None
        for _, candidate in TEST_ALIASES.items():
            canonical_name, alias_pattern = candidate
            if re.search(r"(?:^|\b)" + alias_pattern + r"(?:\b|$)", line, re.I):
                if not re.search(r"test|parameter|laboratory", line, re.I):
                    matched_name = (canonical_name, alias_pattern)
                    break
        if matched_name is None:
            continue

        canonical_name, alias_pattern = matched_name
        name_match = re.search(alias_pattern, line, re.I)
        block = line[name_match.end():].strip() if name_match else ""

        for following in lines[line_index + 1:line_index + 5]:
            if any(re.search(r"(?:^|\b)" + candidate_alias + r"(?:\b|$)", following, re.I)
                   for _, (_, candidate_alias) in TEST_ALIASES.items()):
                break
            block += " " + following

        value_match = re.search(r"[-+]?\d+(?:[.,]\d+)?", block)
        if not value_match:
            continue

        value = parse_number(value_match.group(0))
        after_value = block[value_match.end():]
        unit_match = re.search(UNIT_PATTERN, after_value, re.I)
        unit = unit_match.group(0).strip() if unit_match else ""

        range_match = re.search(r"(?<![A-Za-z])(\d+(?:\.\d+)?\s*(?:-|–|to)\s*(?:[A-Za-z]+\s*)?\d+(?:\.\d+)?)(?![A-Za-z])", block, re.I)
        if range_match:
            reference_range = range_match.group(1).strip()
        else:
            plain_range = re.search(r"(\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?)", block)
            reference_range = plain_range.group(1).strip() if plain_range else ""

        verification_needed = bool(re.search(r"\d+\s*(?:-|–|to)\s*[A-Za-z]+\s*\d+", reference_range or block, re.I))
        if verification_needed:
            corrupted = re.search(r"(\d+\s*(?:-|–|to)\s*[A-Za-z]+\s*\d+)", block, re.I)
            if corrupted:
                reference_range = corrupted.group(1).strip()

        reported_flag_match = re.search(r"\b(Critical|Low|Normal|High)\b", block, re.I)
        reported_flag = reported_flag_match.group(1).title() if reported_flag_match else ""

        status = "Unknown" if verification_needed else classify_status(value, reference_range, reported_flag)
        confidence = min(0.95, 0.65 + (0.3 * ocr_confidence))
        if verification_needed:
            confidence = min(confidence, 0.55)

        results.append(LabValue(
            test_name=canonical_name,
            value=value,
            unit=unit,
            reference_range=reference_range,
            status=status,
            page_number=page_number,
            confidence=round(confidence, 3),
            original_text=block.strip(),
            reported_flag=reported_flag,
            verification_needed=verification_needed,
        ))

    return results


def extract_lab_values(document_text: str, pages: list[dict] | None = None) -> list[LabValue]:
    results: list[LabValue] = []
    page_text = document_text

    if pages:
        units = [(p["page_number"], p["text"], p.get("confidence", 1.0)) for p in pages]
    else:
        units = [(1, document_text, 1.0)]

    seen: set[tuple[str, float | None, int]] = set()
    for page_number, text, ocr_confidence in units:
        table_results = _extract_table_blocks(text, ocr_confidence, page_number)
        for item in table_results:
            key = (item.test_name.lower(), item.value, page_number)
            if key not in seen:
                seen.add(key)
                results.append(item)

        lines = text.splitlines()
        for line in lines:
            for _, (canonical_name, alias_pattern) in TEST_ALIASES.items():
                name_match = re.search(alias_pattern, line, re.I)
                if not name_match:
                    continue

                remainder = line[name_match.end():]
                value_match = re.search(NUMBER, remainder)
                if not value_match:
                    continue

                value = parse_number(value_match.group(0))
                remainder_after_value = remainder[value_match.end():]

                unit_match = re.search(UNIT_PATTERN, remainder_after_value, re.I)
                unit = unit_match.group(0).strip() if unit_match else ""

                reference_match = re.search(
                    r"(?:\b(?:(?:ref(?:erence)?(?:\s*range)?|normal)\s*[:=]?\s*)?)(\d+(?:\.\d+)?\s*(?:-|–|to)\s*\d+(?:\.\d+)?)",
                    remainder_after_value,
                    re.I,
                )
                reference_range = reference_match.group(1).strip() if reference_match else ""

                status_match = re.search(r"\b(low|normal|high|critical|h|l|n)\b", remainder_after_value, re.I)
                laboratory_status = status_match.group(1) if status_match else ""
                status = classify_status(value, reference_range, laboratory_status)

                key = (canonical_name.lower(), value, page_number)
                if key in seen:
                    continue
                seen.add(key)
                confidence = min(0.95, 0.65 + (0.3 * ocr_confidence))
                results.append(LabValue(
                    test_name=canonical_name,
                    value=value,
                    unit=unit,
                    reference_range=reference_range,
                    status=status,
                    page_number=page_number,
                    confidence=round(confidence, 3),
                    original_text=line.strip(),
                ))
                break

    return results
