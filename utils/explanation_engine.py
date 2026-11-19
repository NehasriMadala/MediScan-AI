from __future__ import annotations

from typing import Iterable


TEST_CONTEXT = {
    "Hemoglobin": ("Hemoglobin is a protein in red blood cells that carries oxygen around the body.", "Iron deficiency, nutrition, blood loss, and other health factors can be associated with a change."),
    "RBC": ("RBC count estimates the number of red blood cells in your blood.", "Hydration, altitude, nutrition, bleeding, and bone marrow conditions may be associated with changes."),
    "WBC": ("WBC count measures cells involved in immune defense.", "Infection, inflammation, stress, medicines, and blood disorders may be associated with changes."),
    "Platelet Count": ("Platelets help blood form clots.", "Infection, bleeding, medicines, inflammation, and bone marrow conditions may be associated with changes."),
    "Hematocrit": ("Hematocrit is the percentage of blood volume made up by red blood cells.", "Hydration, bleeding, and red blood cell disorders may be associated with changes."),
    "MCV": ("MCV describes the average size of red blood cells.", "Iron, vitamin B12, or folate status and inherited red blood cell conditions may be associated with changes."),
    "MCH": ("MCH is the average amount of hemoglobin in each red blood cell.", "Red blood cell and nutrient-related conditions may be associated with changes."),
    "MCHC": ("MCHC measures the average hemoglobin concentration inside red blood cells.", "Red blood cell size and nutrient-related conditions may be associated with changes."),
    "Neutrophils": ("Neutrophils are immune cells that help fight bacterial infections.", "Infection, inflammation, stress, medicines, and bone marrow conditions may be associated with changes."),
    "Lymphocytes": ("Lymphocytes are immune cells involved in viral defense and immune memory.", "Infections, immune conditions, stress, and medicines may be associated with changes."),
    "Blood Glucose": ("Blood glucose is the amount of sugar circulating in your blood.", "Food timing, medicines, stress, activity, diabetes, or illness may be associated with changes."),
    "HbA1c": ("HbA1c reflects average blood glucose over roughly the preceding months.", "Glucose control, anemia, kidney disease, and laboratory differences may affect interpretation."),
    "Total Cholesterol": ("Total cholesterol measures the cholesterol circulating in your blood.", "Diet, genetics, activity, weight, medicines, and metabolic conditions may be associated with changes."),
    "HDL": ("HDL is a cholesterol-carrying fraction often called helpful cholesterol.", "Activity, smoking, medicines, genetics, and metabolic health may be associated with changes."),
    "LDL": ("LDL is a cholesterol-carrying fraction that can contribute to artery plaque.", "Diet, genetics, activity, weight, medicines, and metabolic health may be associated with changes."),
    "Triglycerides": ("Triglycerides are a form of fat used by the body for energy.", "Food timing, alcohol, diabetes, medicines, and genetics may be associated with changes."),
    "Creatinine": ("Creatinine is a waste product used as one indicator of kidney function.", "Kidney function, muscle mass, dehydration, medicines, and recent exercise may affect the result."),
    "Urea": ("Urea is a waste product produced from protein breakdown and cleared mainly by the kidneys.", "Kidney function, hydration, diet, bleeding, and liver function may affect the result."),
    "TSH": ("TSH is a signal from the pituitary gland that helps regulate thyroid hormone production.", "Thyroid, pituitary, medication, illness, and laboratory timing factors may affect interpretation."),
    "Vitamin B12": ("Vitamin B12 supports red blood cell formation and nerve function.", "Diet, absorption, medicines, and stomach or intestinal conditions may be associated with changes."),
    "Vitamin D": ("Vitamin D supports bone, muscle, and immune health.", "Sun exposure, diet, absorption, kidney function, and supplements may affect the result."),
    "SGOT/AST": ("AST is an enzyme present in the liver and several other tissues.", "Liver injury, muscle injury, medicines, alcohol, or infection may be associated with changes."),
    "SGPT/ALT": ("ALT is an enzyme mainly associated with liver cells.", "Liver injury, medicines, alcohol, metabolic health, or muscle conditions may be associated with changes."),
    "Bilirubin": ("Bilirubin is a pigment released when red blood cells are broken down.", "Liver function, bile flow, red blood cell breakdown, fasting, and inherited conditions may affect it."),
    "Calcium": ("Calcium is important for bones, nerves, muscles, and heart rhythm.", "Albumin level, kidney function, parathyroid function, diet, medicines, and laboratory timing may affect interpretation."),
    "Sodium": ("Sodium helps regulate fluid balance and nerve and muscle function.", "Fluid intake, dehydration, kidney, heart, or hormone conditions and medicines may affect it."),
    "Potassium": ("Potassium helps nerves and muscles, including the heart, work normally.", "Kidney function, medicines, hydration, diet, and sample handling may affect it."),
    "ESR": ("ESR measures how quickly red blood cells settle and may rise with inflammation.", "Infection, inflammation, anemia, age, and some chronic conditions may affect it."),
}


def format_status(value: float | None, status: str) -> str:
    if value is None:
        return "The value is missing or unreadable"
    return f"Your reported value is {value:g}" if status != "Unknown" else f"Your extracted value is {value:g}"


def explain_lab_results(rows: Iterable[dict], mode: str = "Simple English") -> dict:
    counts = {"Normal": 0, "Low": 0, "High": 0, "Unknown": 0, "Critical": 0}
    findings = []
    explanations = []

    for row in rows:
        test_name = str(row.get("test_name") or row.get("test") or "Medical test")
        value = row.get("value")
        unit = str(row.get("unit") or "")
        reference = str(row.get("reference_range") or row.get("reference") or "")
        status = str(row.get("status") or "Unknown")
        counts[status] = counts.get(status, 0) + 1

        description, factors = TEST_CONTEXT.get(test_name, (
            f"{test_name} is a laboratory marker from this report.",
            "Several factors can influence this laboratory result, so context from a clinician is important.",
        ))

        unit_text = f" {unit}" if unit else ""
        if row.get("verification_needed"):
            reference = str(row.get("reference_range") or reference or "Corrupted/unreadable range")
        if row.get("verification_needed"):
            range_text = f" The OCR range is {reference}. This range requires verification against the original report; it has not been corrected automatically."
        else:
            range_text = f" The reference range printed in this report is {reference}.{'' if reference else ' No reference range was reliably extracted.'}"
        if row.get("verification_needed"):
            status_text = " Low/normal/high classification is intentionally unavailable until the range is verified."
        else:
            status_text = f" This result is classified as **{status.upper()}** based on the report-provided range/flag." if reference or status != "Unknown" else " A reliable low/normal/high classification is unavailable without a usable reference range."
        value_text = f"Your reported result is {value:g}{unit_text}." if isinstance(value, (int, float)) else "A reliable numeric result could not be extracted."

        if mode == "Detailed Medical Explanation":
            body = f"{description} {value_text}{range_text}{status_text} Clinically, {factors.lower()}"
        else:
            body = f"{description} {value_text}{range_text}{status_text} This can be associated with several factors, including {factors.lower()} It does not by itself establish a diagnosis."

        questions = f"Ask your doctor how this result relates to your symptoms, medical history, medicines, and any need for repeat or follow-up testing."
        explanations.append({
            "test": test_name,
            "value": value,
            "unit": unit,
            "reference_range": reference,
            "status": status,
            "page_number": row.get("page_number", 1),
            "explanation": body,
            "questions": questions,
        })

        if status in {"Low", "High", "Critical"}:
            findings.append(f"{test_name}: {value:g}{unit_text} is marked {status.lower()}" + (f" against a reported range of {reference}" if reference else "."))

    abnormal = counts["Low"] + counts["High"] + counts["Critical"]
    summary = (
        f"The report contains {len(explanations)} extracted laboratory parameters: "
        f"{counts['Normal']} normal, {counts['Low']} low, {counts['High']} high, "
        f"and {counts['Unknown']} uncertain or unclassified."
    )
    if abnormal:
        summary += " The findings marked outside the printed range may be useful to discuss with a qualified healthcare professional."
    else:
        summary += " This summary does not replace interpretation in the context of symptoms and medical history."

    return {
        "summary": summary,
        "counts": counts,
        "findings": findings,
        "explanations": explanations,
        "question_suggestions": [
            "How do these results relate to my symptoms and medical history?",
            "Are any results affected by medicines, diet, hydration, or sample timing?",
            "Should any result be repeated or checked with a follow-up test?",
            "Which findings need attention soon, and which should be monitored over time?",
        ],
    }
