from __future__ import annotations

import re


def normalize_test_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.lower())


def units_compatible(previous_unit: str, current_unit: str) -> bool:
    left = previous_unit.lower().replace(" ", "")
    right = current_unit.lower().replace(" ", "")
    if not left or not right:
        return False
    if left == right:
        return True
    aliases = (
        {"mg/dl", "mgdl", "milligram/deciliter"},
        {"mmol/l", "mmoll", "millimole/liter"},
        {"g/dl", "gdl", "gram/deciliter"},
        {"uiu/ml", "miu/l", "mui/l", "microunit/ml"},
    )
    return any(left in group and right in group for group in aliases)


def compare_reports(previous_params: list[dict], current_params: list[dict]) -> list[dict]:
    previous_by_name = {normalize_test_name(item["test_name"]): item for item in previous_params}
    comparisons = []

    for current in current_params:
        key = normalize_test_name(current["test_name"])
        previous = previous_by_name.get(key)
        if not previous:
            continue

        previous_value = previous.get("value")
        current_value = current.get("value")
        previous_unit = previous.get("unit", "")
        current_unit = current.get("unit", "")

        row = {
            "parameter": current["test_name"],
            "previous": previous_value,
            "current": current_value,
            "previous_unit": previous_unit,
            "current_unit": current_unit,
            "absolute_difference": None,
            "percentage_difference": None,
            "previous_reference_range": previous.get("reference_range", ""),
            "current_reference_range": current.get("reference_range", ""),
            "previous_status": previous.get("status", "Unknown"),
            "current_status": current.get("status", "Unknown"),
            "trend_direction": "Unavailable",
            "comparison_available": False,
        }

        if (previous_value is not None and current_value is not None
                and units_compatible(previous_unit, current_unit)):
            difference = round(float(current_value) - float(previous_value), 6)
            row["absolute_difference"] = difference
            row["comparison_available"] = True
            row["trend_direction"] = "Increased" if difference > 0 else "Decreased" if difference < 0 else "Unchanged"
            if float(previous_value) != 0:
                row["percentage_difference"] = round((difference / abs(float(previous_value))) * 100, 2)
        comparisons.append(row)

    return comparisons
