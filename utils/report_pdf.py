from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


DISCLAIMER = "This report is for educational purposes only and is not medical advice. Laboratory findings must be interpreted with symptoms, medical history, and guidance from a qualified healthcare professional."


def generate_summary_pdf(patient_name: str, report_name: str, lab_rows: list[dict], analysis: dict,
                         guidance: dict | None = None, doctor_questions: list[str] | None = None) -> bytes:
    buffer = io.BytesIO()
    document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleCenter", parent=styles["Title"], alignment=TA_CENTER, textColor=colors.HexColor("#7c2d12"))

    flow = [
        Paragraph("MediScan AI - Medical Report Summary", title),
        Spacer(1, 0.18 * inch),
        Paragraph(f"<b>Patient/Profile:</b> {patient_name}", styles["Normal"]),
        Paragraph(f"<b>Report:</b> {report_name}", styles["Normal"]),
        Spacer(1, 0.12 * inch),
        Paragraph("Overall Summary", styles["Heading2"]),
        Paragraph(analysis.get("summary", "No analysis summary is available."), styles["Normal"]),
    ]

    table_data = [["Test", "Result", "Unit", "Reference", "Status", "Page"]]
    for row in lab_rows:
        table_data.append([
            str(row.get("test_name", "")),
            str(row.get("value", "") if row.get("value") is not None else "Unavailable"),
            str(row.get("unit", "")),
            str(row.get("reference_range", "Unavailable")),
            str(row.get("status", "Unknown")),
            str(row.get("page_number", "")),
        ])

    table = Table(table_data, repeatRows=1, colWidths=[95, 62, 58, 90, 68, 38])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fce7f3")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#9d174d")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#d8a6ba")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fff7fb")]),
    ]))
    flow.extend([Spacer(1, 0.18 * inch), Paragraph("Laboratory Values", styles["Heading2"]), table])

    flow.extend([Spacer(1, 0.18 * inch), Paragraph("Patient-Friendly Explanations", styles["Heading2"])])
    for item in analysis.get("explanations", []):
        flow.append(Paragraph(f"<b>{item['test']}</b>", styles["Heading3"]))
        flow.append(Paragraph(item["explanation"], styles["Normal"]))

    guidance = guidance or {"nutrition": [], "next_steps": {"precautions": [], "considerations": [], "urgent_warning": "", "restrictions": []}}
    if guidance["nutrition"]:
        flow.extend([Spacer(1, 0.18 * inch), Paragraph("Food and Nutrition Guidance", styles["Heading2"])])
        for item in guidance["nutrition"]:
            flow.append(Paragraph(f"<b>{item['title']}</b> — relevant finding: {item['test']} ({item['status']})", styles["Heading3"]))
            for food in item["foods"]:
                flow.append(Paragraph(f"- {food}", styles["Normal"]))
            flow.append(Paragraph(item["why"], styles["Normal"]))

    next_steps = guidance["next_steps"]
    flow.extend([Spacer(1, 0.18 * inch), Paragraph("What Should I Do Next?", styles["Heading2"])])
    for item in next_steps["precautions"]:
        flow.append(Paragraph(f"- {item}", styles["Normal"]))
    for item in next_steps["considerations"]:
        flow.append(Paragraph(f"- {item}", styles["Normal"]))
    if next_steps["restrictions"]:
        for item in next_steps["restrictions"]:
            flow.append(Paragraph(f"Profile consideration: {item}", styles["Normal"]))

    flow.extend([Spacer(1, 0.18 * inch), Paragraph("Questions to Discuss", styles["Heading2"])])
    questions = doctor_questions if doctor_questions is not None else analysis.get("question_suggestions", [])
    for question in questions:
        flow.append(Paragraph(f"- {question}", styles["Normal"]))

    flow.extend([Spacer(1, 0.18 * inch), Paragraph("Medical Disclaimer", styles["Heading2"]), Paragraph(DISCLAIMER, styles["Normal"])])
    document.build(flow)
    return buffer.getvalue()
