from __future__ import annotations

from typing import Iterable


FOOD_GUIDANCE = {
    "Hemoglobin": {
        "title": "Iron and vitamin C-rich foods",
        "foods": ["Spinach and lentils", "Beans and chickpeas", "Iron-fortified cereals", "Guava, oranges and lemon", "Lean meat or fish where suitable"],
        "why": "Vitamin C-rich fruits may help the body absorb iron from plant foods. This is general education, not proof that food will correct anemia.",
    },
    "Vitamin B12": {
        "title": "Vitamin B12 food sources",
        "foods": ["Milk or fortified plant milk", "Eggs", "Fish", "Fortified foods", "Meat or dairy if included in the person's diet"],
        "why": "These foods contain vitamin B12, but diet-related and absorption-related causes are different. Supplements should not be started without clinician guidance.",
    },
    "Vitamin D": {
        "title": "Vitamin D food and sunlight context",
        "foods": ["Fortified milk or alternatives", "Eggs", "Fatty fish where appropriate", "Fortified cereals"],
        "why": "Vitamin D status can reflect diet, sunlight exposure and absorption. Safe sunlight guidance and supplements need individual medical context.",
    },
    "Total Cholesterol": {
        "title": "Fiber and heart-supportive dietary patterns",
        "foods": ["Fruits and vegetables", "Whole grains", "Beans and lentils", "Nuts in portions that suit the person", "Foods lower in saturated and trans fats"],
        "why": "A fiber-rich dietary pattern is associated with healthier cholesterol over time. One result does not determine whether dietary change or treatment is needed.",
    },
    "LDL": {
        "title": "Lower-saturated-fat dietary pattern",
        "foods": ["Vegetables and fruit", "Oats and barley", "Beans and lentils", "Unsaturated oils in moderation"],
        "why": "Dietary patterns rich in fiber and unsaturated fats may help support cholesterol management. Discuss individual targets with a clinician.",
    },
    "Triglycerides": {
        "title": "Meal and carbohydrate guidance",
        "foods": ["Whole grains and legumes", "Vegetables", "Water instead of sugary drinks", "Food portions suitable for individual needs"],
        "why": "Food timing, alcohol, carbohydrate intake and metabolic conditions may affect triglycerides. A clinician can personalize guidance.",
    },
    "Calcium": {
        "title": "Calcium food sources",
        "foods": ["Milk or fortified alternatives", "Yogurt if tolerated", "Calcium-set tofu", "Leafy vegetables"],
        "why": "These foods provide dietary calcium, but kidney disease and milk allergy or intolerance can change what is appropriate.",
    },
    "Potassium": {
        "title": "Potassium requires individualized review",
        "foods": ["Only discuss adding potassium-rich foods with the care team", "Avoid potassium supplements unless prescribed", "Ask for kidney-specific dietary advice"],
        "why": "Potassium can be dangerous when kidney function or medicines affect potassium balance. Do not add high-potassium foods or supplements from this page alone.",
    },
    "Creatinine": {
        "title": "Kidney-aware general nutrition",
        "foods": ["Do not change protein intake without advice", "Ask about fluid needs", "Choose a balanced diet appropriate for kidney health"],
        "why": "Creatinine needs kidney and muscle context. Restrictive or high-protein diets may be unsuitable.",
    },
}


def generate_guidance(rows: Iterable[dict], patient_profile: dict | None = None) -> dict:
    profile = patient_profile or {}
    by_name = {str(row.get("test_name") or row.get("test") or ""): row for row in rows}
    relevant = []

    for test_name, guidance in FOOD_GUIDANCE.items():
        row = by_name.get(test_name)
        if not row:
            continue
        status = str(row.get("status") or "Unknown")
        should_show = status in {"Low", "High"}
        if test_name in {"Potassium", "Creatinine"}:
            should_show = status != "Normal"
        if should_show:
            relevant.append({
                "test": test_name,
                "status": status,
                "title": guidance["title"],
                "foods": list(guidance["foods"]),
                "why": guidance["why"],
            })

    precautions = [
        "Maintain regular meals, hydration and sleep unless a healthcare professional has given a fluid or diet restriction.",
        "Avoid self-medicating or starting supplements based only on a laboratory result.",
        "Bring this report, a medicine list and questions to the appointment.",
        "If symptoms are new or worsening, seek professional advice rather than relying on laboratory values alone.",
    ]

    restrictions = []
    if profile.get("kidney_disease"):
        restrictions.append("A kidney condition may require restriction of potassium, sodium, protein or fluid; obtain kidney-specific dietary advice.")
    if profile.get("diabetes"):
        restrictions.append("Food and carbohydrate advice should account for diabetes treatment and glucose targets.")
    if profile.get("pregnancy"):
        restrictions.append("Pregnancy may change suitable nutrition and supplement advice; discuss all changes with an obstetric clinician.")
    if profile.get("allergies"):
        restrictions.append("Avoid listed foods that conflict with allergies or dietary restrictions.")

    next_steps = {
        "precautions": precautions,
        "considerations": [
            "Discuss every abnormal or unclassified result with the appropriate healthcare professional.",
            "Ask whether symptoms, medicines, hydration, sample timing or recent illness could affect interpretation.",
            "Ask which abnormal findings, if any, should be repeated or followed up.",
        ],
        "urgent_warning": "Seek urgent medical attention for severe breathing difficulty, chest pain, fainting, severe weakness, confusion, uncontrolled bleeding or other suddenly severe symptoms.",
        "restrictions": restrictions,
    }

    return {"nutrition": relevant, "next_steps": next_steps}
