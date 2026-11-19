from __future__ import annotations

from typing import Iterable


def generate_doctor_questions(rows: Iterable[dict], comparison: list[dict] | None = None) -> list[str]:
    questions = []
    abnormal_tests = []

    for row in rows:
        test_name = str(row.get("test_name") or row.get("test") or "this test")
        status = str(row.get("status") or "Unknown")
        value = row.get("value")
        unit = str(row.get("unit") or "")
        reference = str(row.get("reference_range") or "")

        if row.get("verification_needed"):
            questions.append(f"The extracted range for {test_name} appears uncertain. Can you verify the original range and whether this result is normal?")
        elif status in {"Low", "High", "Critical"}:
            abnormal_tests.append(test_name)
            questions.append(f"What could explain my {test_name} result of {value:g}{(' ' + unit) if unit else ''}" + (f", compared with the report range {reference}" if reference else "") + "?")
            questions.append(f"Do I need additional testing or follow-up for {test_name}, and when would it be reasonable to repeat it?")

    if "Hemoglobin" in abnormal_tests:
        questions.extend([
            "Do my RBC, MCV, MCH and MCHC values provide additional information about my low hemoglobin?",
            "Could diet, bleeding, medicines or another cause be relevant to this result?",
        ])

    if "Total Cholesterol" in abnormal_tests or "LDL" in abnormal_tests:
        questions.extend([
            "Which lipid value needs the most attention based on my overall health?",
            "What dietary and lifestyle changes should I discuss in my situation?",
            "How should these values influence the timing of repeat testing?",
        ])

    if "Vitamin B12" in abnormal_tests:
        questions.extend([
            "What could be contributing to this vitamin B12 result?",
            "Could dietary habits or absorption be relevant, and should additional investigations be considered?",
        ])

    if "Vitamin D" in abnormal_tests:
        questions.extend([
            "What could be contributing to this vitamin D result?",
            "Should I consider dietary, sunlight or supplementation advice from a clinician?",
        ])

    if comparison:
        changed = [row["parameter"] for row in comparison if row.get("comparison_available")]
        if changed:
            questions.append("How should I interpret changes in " + ", ".join(changed[:5]) + " across the two reports?")

    if not abnormal_tests:
        questions.extend([
            "Do these extracted results need any context from my symptoms or medical history?",
            "Are there any findings that should be repeated or monitored over time?",
        ])

    questions.extend([
        "Which symptoms or changes should prompt me to contact you sooner?",
        "What information or documents should I bring to my next appointment?",
    ])

    unique = []
    for question in questions:
        if question not in unique:
            unique.append(question)
    return unique[:15]
