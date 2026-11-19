from __future__ import annotations

import io
import os
from dataclasses import asdict, dataclass
from pathlib import Path

import fitz
from PIL import Image, ImageOps


SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_MB", "20")) * 1024 * 1024
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "30"))


@dataclass
class PageResult:
    page_number: int
    text: str
    extraction_method: str
    confidence: float
    low_quality: bool
    warning: str = ""


@dataclass
class DocumentResult:
    document_name: str
    document_type: str
    page_count: int
    pages: list[PageResult]
    text: str


def validate_upload(file_name: str, content: bytes) -> tuple[str, str]:
    suffix = Path(file_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError("Unsupported file type. Upload JPG, JPEG, PNG, or PDF.")
    if not content:
        raise ValueError("The uploaded file is empty.")
    if len(content) > MAX_UPLOAD_BYTES:
        raise ValueError(f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB upload limit.")

    if suffix == ".pdf":
        if not content.startswith(b"%PDF"):
            raise ValueError("The PDF header is invalid or the file is corrupted.")
        return suffix, "pdf"

    try:
        with Image.open(io.BytesIO(content)) as image:
            image.verify()
    except Exception as exc:
        raise ValueError("The image is corrupted or unreadable.") from exc
    return suffix, "image"


def preprocess_image(image: Image.Image) -> Image.Image:
    import cv2
    import numpy as np

    rgb = np.array(image.convert("RGB"))
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    gray = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    coords = cv2.findNonZero(cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1])
    if coords is not None and len(coords) > 20:
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = 90 + angle
        if abs(angle) > 0.5:
            center = (gray.shape[1] // 2, gray.shape[0] // 2)
            matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
            gray = cv2.warpAffine(gray, matrix, (gray.shape[1], gray.shape[0]), flags=cv2.INTER_CUBIC,
                                  borderMode=cv2.BORDER_REPLICATE)

    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    threshold = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 31, 10)
    return Image.fromarray(threshold)


def ocr_image(image: Image.Image) -> tuple[str, float]:
    try:
        import pytesseract
    except ImportError as exc:
        raise RuntimeError("OCR support is not installed. Install pytesseract and the Tesseract executable.") from exc

    tesseract_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if not tesseract_cmd:
        windows_default = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        if os.name == "nt" and os.path.exists(windows_default):
            tesseract_cmd = windows_default
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    processed = preprocess_image(image)
    data = pytesseract.image_to_data(processed, output_type=pytesseract.Output.DICT)
    words = []
    confidences = []
    for index, word in enumerate(data.get("text", [])):
        if word.strip():
            words.append(word.strip())
            try:
                confidence = float(data["conf"][index])
                if confidence >= 0:
                    confidences.append(confidence)
            except (KeyError, ValueError, TypeError):
                pass

    text = pytesseract.image_to_string(processed, config="--psm 6").strip()
    average = sum(confidences) / len(confidences) if confidences else 0.0
    return text, round(average / 100.0, 3)


def process_image(file_name: str, content: bytes) -> DocumentResult:
    with Image.open(io.BytesIO(content)) as source:
        source = ImageOps.exif_transpose(source).convert("RGB")
        try:
            text, confidence = ocr_image(source)
        except Exception as exc:
            return DocumentResult(
                file_name,
                "Image-based report",
                1,
                [PageResult(1, "", "OCR unavailable", 0.0, True, str(exc))],
                "",
            )
    low_quality = confidence < 0.65 or len(text.strip()) < 20
    warning = "OCR confidence is low; review extracted text before analysis." if low_quality else ""
    page = PageResult(1, text, "OCR", confidence, low_quality, warning)
    return DocumentResult(file_name, "Image-based report", 1, [page], text)


def process_pdf(file_name: str, content: bytes) -> DocumentResult:
    pdf = fitz.open(stream=content, filetype="pdf")
    page_count = pdf.page_count
    if page_count > MAX_PDF_PAGES:
        pdf.close()
        raise ValueError(f"PDF exceeds the {MAX_PDF_PAGES}-page limit.")

    pages: list[PageResult] = []
    for page_number in range(page_count):
        page = pdf.load_page(page_number)
        native = page.get_text("text").strip()
        readable_threshold = 50
        if len(native) >= readable_threshold:
            confidence = 1.0
            page_result = PageResult(page_number + 1, native, "Native text", confidence, False)
        else:
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            image = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
            try:
                text, confidence = ocr_image(image)
            except Exception as exc:
                text = ""
                confidence = 0.0
                page_result = PageResult(page_number + 1, text, "OCR unavailable", confidence, True, str(exc))
            else:
                low_quality = confidence < 0.65 or len(text.strip()) < 20
                warning = "OCR confidence is low; review extracted text before analysis." if low_quality else ""
                page_result = PageResult(page_number + 1, text, "OCR", confidence, low_quality, warning)
        pages.append(page_result)
    pdf.close()

    text = "\n\n".join(f"[PAGE {p.page_number}]\n{p.text}" for p in pages)
    return DocumentResult(file_name, "PDF report", page_count, pages, text)


def process_document(file_name: str, content: bytes) -> DocumentResult:
    _, document_kind = validate_upload(file_name, content)
    if document_kind == "pdf":
        return process_pdf(file_name, content)
    return process_image(file_name, content)


def document_result_dict(result: DocumentResult) -> dict:
    return {
        "document_name": result.document_name,
        "document_type": result.document_type,
        "page_count": result.page_count,
        "text": result.text,
        "pages": [asdict(page) for page in result.pages],
    }
