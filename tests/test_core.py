from pathlib import Path
from tempfile import TemporaryDirectory

import fitz
from PIL import Image, ImageDraw

from utils.document_processor import process_document, validate_upload
from utils.history_store import HistoryStore
from utils.lab_extractor import classify_status, extract_lab_values
from utils.report_comparison import compare_reports, units_compatible


def test_text_pdf_and_multipage():
    with TemporaryDirectory() as directory:
        path = Path(directory) / "report.pdf"
        pdf = fitz.open()
        for number in (1, 2):
            page = pdf.new_page()
            page.insert_text((72, 72), f"Hemoglobin {10.5 + number / 10:.1f} g/dL 12.0-15.0 Low")
            page.insert_text((72, 92), "WBC 7500 cells/uL 4000-11000 Normal")
        pdf.save(path)
        pdf.close()

        result = process_document(path.name, path.read_bytes())
        values = extract_lab_values(result.text, [{"page_number": p.page_number, "text": p.text, "confidence": p.confidence} for p in result.pages])

        assert result.page_count == 2
        assert all(p.extraction_method == "Native text" for p in result.pages)
        assert len(values) >= 4


def test_jpg_jpeg_png_validation():
    with TemporaryDirectory() as directory:
        for suffix in (".jpg", ".jpeg", ".png"):
            path = Path(directory) / ("report" + suffix)
            image = Image.new("RGB", (300, 120), "white")
            ImageDraw.Draw(image).text((20, 40), "Hemoglobin 11.2 g/dL 12.0-15.0", fill="black")
            image.save(path)
            kind = validate_upload(path.name, path.read_bytes())[1]
            assert kind == "image"


def test_corrupted_and_unsupported_files():
    try:
        validate_upload("report.txt", b"text")
        assert False
    except ValueError:
        pass

    try:
        validate_upload("broken.png", b"not an image")
        assert False
    except ValueError:
        pass


def test_lab_reference_and_missing_reference():
    values = extract_lab_values("Hemoglobin 11.2 g/dL 12.0-15.0 Low\nPotassium 4.5 mmol/L")
    assert classify_status(11.2, "12.0-15.0") == "Low"
    assert classify_status(11.2, "") == "Unknown"
    assert len(values) >= 2


def test_manual_correction_model_shape():
    values = extract_lab_values("Creatinine 1.1 mg/dL 0.7-1.3")
    values[0].value = 1.2
    values[0].reference_range = "0.7-1.3"
    values[0].status = classify_status(values[0].value, values[0].reference_range)
    assert values[0].value == 1.2
    assert values[0].status == "Normal"


def test_history_and_comparison(tmp_path):
    with TemporaryDirectory(ignore_cleanup_errors=True) as directory:
        store = HistoryStore(Path(directory) / "history.sqlite3")
        patient_id = store.add_patient("Test Patient")
        previous = [{"test_name": "Hemoglobin", "value": 10.5, "unit": "g/dL", "reference_range": "12-15", "status": "Low"}]
        current = [{"test_name": "Hemoglobin", "value": 11.8, "unit": "g/dL", "reference_range": "12-15", "status": "Low"}]

        previous_id = store.save_report(patient_id, "Previous", "2026-01-10", "PDF report", previous, {"pages": []})
        current_id = store.save_report(patient_id, "Current", "2026-06-15", "Image report", current, {"pages": []})

        reports = store.list_reports(patient_id)
        assert len(reports) == 2
        comparison = compare_reports(previous, current)
        assert comparison[0]["absolute_difference"] == 1.3
        assert comparison[0]["comparison_available"] is True

        store.delete_report(previous_id)
        assert len(store.list_reports(patient_id)) == 1
        assert current_id


def test_flattened_cbc_table_reconstructs_rows():
    text = """Test Result Unit Reference range Flag
Hemoglobin 11.2 g/dL 12.0 - 15.0 LOW
RBC Count 4.35 million/µL 4.5 - 5.5 NORMAL
WBC Count 8000 cells/µL 4000 - 11000 NORMAL
Platelet Count 250000 cells/µL 150000 - 450000 NORMAL
Hematocrit 35.5 % 36.0 - 46.0 LOW
MCV 81.6 fL 80 - 100 NORMAL
MCH 25.7 pg 27 - 33 LOW
MCHC 31.5 g/dL 32 - 36 LOW
Neutrophils 60 % 40 - I 75 NORMAL
Lymphocytes 30 % 20 - 40 NORMAL"""
    values = extract_lab_values(text)
    by_name = {item.test_name: item for item in values}

    assert by_name["Hemoglobin"].value == 11.2
    assert by_name["Hemoglobin"].status == "Low"
    assert by_name["RBC Count"].value == 4.35
    assert by_name["WBC Count"].value == 8000
    assert by_name["Hematocrit"].status == "Low"
    assert by_name["Neutrophils"].verification_needed is True
    assert by_name["Neutrophils"].status == "Unknown"


def test_dynamic_cbc_extraction_and_explanation():
    text = """Hemoglobin 11.2 g/dL 12.0-15.0 Low
Hematocrit 33.1 % 36.0-46.0 Low
MCV 88 fL 80-100 Normal
Platelet Count 210000 /uL 150000-450000 Normal"""
    values = extract_lab_values(text)
    assert any(item.test_name == "Hemoglobin" and item.status == "Low" for item in values)
    assert any(item.test_name == "Hematocrit" for item in values)
    assert any(item.test_name == "MCV" for item in values)

    from utils.explanation_engine import explain_lab_results
    analysis = explain_lab_results([item.model_dump() for item in values])
    assert "11.2" in analysis["summary"] or len(analysis["explanations"]) >= 3
    assert analysis["counts"]["Low"] >= 1


def test_nutrition_and_doctor_guidance_are_report_specific():
    from utils.guidance_engine import generate_guidance
    from utils.doctor_questions import generate_doctor_questions

    rows = [{"test_name": "Hemoglobin", "value": 11.2, "unit": "g/dL", "reference_range": "12.0-15.0", "status": "Low", "verification_needed": False}]
    guidance = generate_guidance(rows, {"kidney_disease": False, "diabetes": False, "pregnancy": False, "allergies": ""})
    assert any(item["test"] == "Hemoglobin" for item in guidance["nutrition"])
    assert guidance["nutrition"][0]["why"]

    questions = generate_doctor_questions(rows)
    assert any("Hemoglobin" in question for question in questions)


def test_profile_restrictions_are_added_to_guidance():
    from utils.guidance_engine import generate_guidance
    guidance = generate_guidance([], {"kidney_disease": True, "diabetes": False, "pregnancy": False, "allergies": "Peanuts"})
    assert len(guidance["next_steps"]["restrictions"]) >= 1


def test_pdf_summary_generation():
    from utils.report_pdf import generate_summary_pdf
    lab_rows = [{"test_name": "Hemoglobin", "value": 11.2, "unit": "g/dL", "reference_range": "12.0-15.0", "status": "Low", "page_number": 1}]
    from utils.explanation_engine import explain_lab_results
    analysis = explain_lab_results(lab_rows)
    pdf = generate_summary_pdf("Test Patient", "CBC", lab_rows, analysis)
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_different_units_mark_comparison_unavailable():
    previous = [{"test_name": "Glucose", "value": 100, "unit": "mg/dL", "reference_range": "70-99", "status": "High"}]
    current = [{"test_name": "Glucose", "value": 5.5, "unit": "mmol/L", "reference_range": "", "status": "Unknown"}]
    result = compare_reports(previous, current)
    assert units_compatible("mg/dL", "mmol/L") is False
    assert result[0]["comparison_available"] is False
