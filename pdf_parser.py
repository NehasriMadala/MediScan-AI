from pathlib import Path

from utils.document_processor import process_document
from utils.lab_extractor import extract_lab_values as extract_structured_values


def extract_lab_values(pdf_path: str) -> list[dict]:
    """Backward-compatible PDF entry point using the universal processor."""
    path = Path(pdf_path)
    result = process_document(path.name, path.read_bytes())
    values = extract_structured_values(result.text, document_result_dict_pages(result))

    return [
        {
            "test": item.test_name,
            "test_name": item.test_name,
            "value": item.value,
            "unit": item.unit,
            "reference": item.reference_range or "N/A",
            "reference_range": item.reference_range,
            "status": item.status,
            "page_number": item.page_number,
            "confidence": item.confidence,
            "original_text": item.original_text,
        }
        for item in values
    ]


def document_result_dict_pages(result) -> list[dict]:
    return [
        {
            "page_number": page.page_number,
            "text": page.text,
            "confidence": page.confidence,
        }
        for page in result.pages
    ]
