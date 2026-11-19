import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

import streamlit as st
from dotenv import load_dotenv

load_dotenv(override=True)

from agents import invoke_llm, reset_llm, validate_groq_api_key  # noqa: E402
from graph import build_graph
from pdf_parser import extract_lab_values
from utils.document_processor import process_document, validate_upload
from utils.history_store import HistoryStore
from utils.lab_extractor import LabValue, extract_lab_values as extract_structured_values
from utils.report_comparison import compare_reports
from utils.explanation_engine import explain_lab_results
from utils.report_pdf import generate_summary_pdf
from database.patient_repository import PatientRepository, ProfileValidationError
from utils.guidance_engine import generate_guidance
from utils.doctor_questions import generate_doctor_questions

reset_llm()

st.set_page_config(
    page_title="MediScan AI — Lab Report Simplifier",
    page_icon="🩺",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    :root {
        --bg:         #F4F7F8;
        --surface:    #FFFFFF;
        --surface2:   #FDE8F0;
        --border:     rgba(254,129,212,0.18);
        --border-med: rgba(254,129,212,0.30);
        --heading:    #17313B;
        --body:       #3E535C;
        --muted:      #6B7F87;
        --pink:       #168C8C;
        --rose:       #147A7A;
        --blush:      #FBC3C1;
        --peach:      #FFEABB;
        --green:      #16a34a;
        --green-lit:  #22c55e;
        --blue:       #2563eb;
        --blue-lit:   #3b82f6;
        --hover-glow: rgba(254,129,212,0.20);
    }

    html, body, [class*="css"] {
        font-family: 'Sora', sans-serif;
        background-color: var(--bg) !important;
        color: var(--heading) !important;
    }

    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding: 2rem 3rem 4rem !important; max-width: 1100px !important; }

    /* ── Hero ── */
    section[data-testid="stSidebar"] {
        background: #FFFFFF !important;
        border-right: 1px solid #E5ECEE !important;
        min-width: 230px !important;
    }
    section[data-testid="stSidebar"] [role="radiogroup"] label { border-radius: 8px; padding: 0.35rem 0.55rem; }
    section[data-testid="stSidebar"] [role="radiogroup"] label[data-selected="true"] { background: #E8F5F4; color: #147A7A; }
    .block-container { background: #F4F7F8 !important; }
    .hero {
        background: linear-gradient(135deg, #DDF3F1 0%, #F7FAFA 55%, #EAF1F5 100%);
        border: 1px solid var(--border-med);
        border-radius: 20px;
        padding: 2.8rem 3rem;
        margin-bottom: 2rem;
        position: relative;
        overflow: hidden;
        box-shadow: 0 4px 28px rgba(200,60,120,0.22);
        border: 1.5px solid rgba(254,129,212,0.45);
    }
    .hero::before {
        content: '';
        position: absolute;
        top: -60px; right: -40px;
        width: 240px; height: 240px;
        background: radial-gradient(circle, rgba(254,129,212,0.22) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero::after {
        content: '';
        position: absolute;
        bottom: -50px; left: 50px;
        width: 200px; height: 200px;
        background: radial-gradient(circle, rgba(255,234,187,0.35) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(254,129,212,0.15);
        border: 1px solid rgba(254,129,212,0.45);
        color: #c0397a;
        font-size: 0.7rem;
        font-weight: 600;
        letter-spacing: 1.2px;
        text-transform: uppercase;
        padding: 3px 12px;
        border-radius: 20px;
        margin-bottom: 0.9rem;
    }
    .hero-title {
        font-size: 2.6rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin: 0 0 0.5rem;
        background: linear-gradient(90deg, #1a0f14 0%, #c0397a 50%, #d4860a 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-sub {
        font-size: 1rem;
        color: var(--muted);
        font-weight: 300;
        margin: 0;
        max-width: 600px;
    }

    /* ── Tip box ── */
    .tip-box {
        background: var(--surface);
        border: 1px solid var(--border-med);
        border-radius: 14px;
        padding: 1.1rem 1.3rem;
        font-size: 0.8rem;
        color: var(--muted);
        line-height: 1.95;
        box-shadow: 0 2px 8px rgba(254,129,212,0.08);
    }

    /* ── Stats bar ── */
    .stats-bar {
        display: flex;
        gap: 0.8rem;
        margin-bottom: 1.4rem;
        flex-wrap: wrap;
    }
    .stat-pill {
        background: var(--surface);
        border: 1px solid var(--border-med);
        border-radius: 10px;
        padding: 0.45rem 1rem;
        font-size: 0.82rem;
        color: var(--muted);
        box-shadow: 0 1px 4px rgba(254,129,212,0.07);
    }
    .stat-pill strong { color: var(--heading); }

    /* ── Section headings ── */
    .section-head {
        display: flex;
        align-items: center;
        gap: 0.65rem;
        font-size: 1.1rem;
        font-weight: 600;
        color: var(--heading);
        margin: 2.2rem 0 1rem;
        padding-bottom: 0.55rem;
        border-bottom: 1.5px solid var(--border-med);
    }
    .section-head .dot {
        width: 9px; height: 9px;
        border-radius: 50%;
        flex-shrink: 0;
    }

    /* ── Explanation cards ── */
    .explain-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 3px solid var(--rose);
        border-radius: 12px;
        padding: 0.95rem 1.2rem;
        margin-bottom: 0.55rem;
        transition: box-shadow 0.2s, border-left-color 0.2s;
        box-shadow: 0 1px 6px rgba(254,129,212,0.06);
    }
    .explain-card:hover {
        box-shadow: 0 4px 16px var(--hover-glow);
        border-left-color: var(--pink);
    }
    .explain-test {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.78rem;
        font-weight: 600;
        color: var(--rose);
        text-transform: uppercase;
        letter-spacing: 0.7px;
        margin-bottom: 0.28rem;
    }
    .explain-text {
        font-size: 0.91rem;
        color: var(--body);
        line-height: 1.6;
        margin: 0;
    }

    /* ── Flag rows ── */
    .flag-row {
        display: flex;
        align-items: flex-start;
        gap: 0.8rem;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.85rem 1.1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 6px rgba(254,129,212,0.06);
        transition: box-shadow 0.2s;
    }
    .flag-row:hover { box-shadow: 0 4px 16px var(--hover-glow); }

    .severity-chip {
        font-size: 0.68rem;
        font-weight: 700;
        letter-spacing: 0.9px;
        text-transform: uppercase;
        padding: 3px 11px;
        border-radius: 20px;
        white-space: nowrap;
        flex-shrink: 0;
        margin-top: 2px;
    }
    .chip-normal   { background: #dcfce7; color: #15803d; border: 1px solid #86efac; }
    .chip-watch    { background: #fef9c3; color: #a16207; border: 1px solid #fde047; }
    .chip-high     { background: #ffedd5; color: #c2410c; border: 1px solid #fdba74; }
    .chip-critical { background: #fce7f3; color: #be185d; border: 1px solid #f9a8d4; }

    .flag-test {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.82rem;
        font-weight: 600;
        color: var(--heading);
    }
    .flag-reason { font-size: 0.87rem; color: var(--muted); margin-top: 2px; }

    /* ── Question cards ── */
    .q-card {
        display: flex;
        gap: 0.8rem;
        align-items: flex-start;
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.5rem;
        box-shadow: 0 1px 6px rgba(254,129,212,0.06);
        transition: box-shadow 0.2s;
    }
    .q-card:hover { box-shadow: 0 4px 16px var(--hover-glow); }
    .q-num {
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        color: var(--blue);
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        font-weight: 700;
        width: 26px; height: 26px;
        border-radius: 7px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
    }
    .q-text { font-size: 0.91rem; color: var(--body); line-height: 1.55; margin: 0; padding-top: 2px; }

    /* ── Disclaimer ── */
    .disclaimer {
        background: #fffbeb;
        border: 1px solid #fde68a;
        border-radius: 12px;
        padding: 0.9rem 1.2rem;
        margin-top: 1.5rem;
        display: flex;
        gap: 0.7rem;
        align-items: flex-start;
    }
    .disclaimer-icon { font-size: 1.1rem; flex-shrink: 0; }
    .disclaimer-text { font-size: 0.84rem; color: #92400e; line-height: 1.55; }

    /* ── Streamlit overrides ── */
    .stButton > button {
        background: #147A7A !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'Sora', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        padding: 0.55rem 1.8rem !important;
        letter-spacing: 0.3px !important;
        transition: box-shadow 0.2s, opacity 0.2s !important;
        box-shadow: 0 2px 10px rgba(190,24,93,0.25) !important;
    }
    .stButton > button:hover {
        box-shadow: 0 4px 20px rgba(190,24,93,0.35) !important;
        opacity: 0.92 !important;
    }
    .stButton > button:disabled { opacity: 0.4 !important; box-shadow: none !important; }

    .stDownloadButton > button {
        background: #eff6ff !important;
        color: var(--blue) !important;
        border: 1px solid #bfdbfe !important;
        border-radius: 10px !important;
        font-family: 'Sora', sans-serif !important;
        font-weight: 600 !important;
    }

    div[data-testid="stFileUploader"] {
        background: var(--surface) !important;
        border: 1.5px dashed rgba(254,129,212,0.4) !important;
        border-radius: 14px !important;
        padding: 0.5rem !important;
    }
    div[data-testid="stExpander"] {
        background: var(--surface) !important;
        border: 1px solid var(--border-med) !important;
        border-radius: 12px !important;
    }
    .stSuccess {
        background: #f0fdf4 !important;
        border: 1px solid #86efac !important;
        border-radius: 10px !important;
        color: #15803d !important;
    }
    .stError {
        background: #fff1f2 !important;
        border: 1px solid #fecdd3 !important;
        border-radius: 10px !important;
    }
    div[data-testid="stSpinner"] p { color: var(--muted) !important; font-size: 0.88rem !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Application state ────────────────────────────────────────────────────────
if "lab_rows" not in st.session_state:
    st.session_state.lab_rows = []
if "documents" not in st.session_state:
    st.session_state.documents = []
if "agent_report" not in st.session_state:
    st.session_state.agent_report = None
if "analysis" not in st.session_state:
    st.session_state.analysis = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "guidance" not in st.session_state:
    st.session_state.guidance = None
if "doctor_questions" not in st.session_state:
    st.session_state.doctor_questions = []
if "active_patient_id" not in st.session_state:
    st.session_state.active_patient_id = None
if "creating_profile" not in st.session_state:
    st.session_state.creating_profile = False
if "patient_profile" not in st.session_state:
    st.session_state.patient_profile = {
        "name": "",
        "age": None,
        "sex": "",
        "kidney_disease": False,
        "diabetes": False,
        "pregnancy": False,
        "allergies": "",
    }

history_store = HistoryStore()
patient_repository = PatientRepository()

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <div class="hero-badge">🧬 AI-Powered · Groq LLM · LangGraph</div>
        <div class="hero-title">MediScan AI</div>
        <p class="hero-sub">Upload medical reports for structured lab results, plain-English explanations, interactive charts, history comparison, and safe AI follow-up questions.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Navigation and API validation ─────────────────────────────────────────────
st.sidebar.markdown("## MediScan AI")
section_label = st.sidebar.radio(
    "Navigation",
    [
        "Home Dashboard",
        "Upload & Analyze",
        "My Medical Reports",
        "Health Insights",
        "Compare Reports",
        "AI Medical Assistant",
        "Patient Profile",
        "Settings",
    ],
    key="main_navigation",
)
section_aliases = {
    "Home Dashboard": "Dashboard",
    "Upload & Analyze": "Upload Medical Report",
    "My Medical Reports": "Medical History",
    "Health Insights": "Visual Analytics",
    "Compare Reports": "Compare Reports",
    "AI Medical Assistant": "AI Medical Assistant",
    "Patient Profile": "Patient Profile",
    "Settings": "Settings",
}
section = section_aliases[section_label]
key_error = validate_groq_api_key()
if key_error:
    st.sidebar.warning("Groq API key required for AI analysis.")

profiles = patient_repository.list_profiles()
patient_names = {item["profile_name"]: item["id"] for item in profiles}
patients = [{"patient_id": profile_id, "display_name": profile_name} for profile_name, profile_id in patient_names.items()]
uploaded = None

# Legacy PDF-only upload surface is disabled; universal upload is rendered below.
col_upload, col_tip = st.columns([2, 1])

with col_upload:
    pass

with col_tip:
    st.markdown(
        """
        <div class="tip-box">
            ✅ Text-based PDFs work best<br>
            ✅ Blood, urine, thyroid reports<br>
            🔒 File not stored anywhere<br>
            ⚡ Results in ~10 seconds
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Processing ────────────────────────────────────────────────────────────────
if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(uploaded.read())
        pdf_path = tmp.name

    with st.spinner("Extracting lab values from PDF…"):
        lab_data = extract_lab_values(pdf_path)

    Path(pdf_path).unlink(missing_ok=True)

    if not lab_data:
        st.error("Could not parse lab values. Please try a text-based (not scanned) PDF.")
        st.stop()

    st.markdown(
        f"""
        <div class="stats-bar">
            <div class="stat-pill">📄 <strong>{uploaded.name}</strong></div>
            <div class="stat-pill">🧪 <strong>{len(lab_data)}</strong> tests detected</div>
            <div class="stat-pill">📦 <strong>{round(uploaded.size/1024, 1)} KB</strong></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("🔬 Preview extracted values"):
        st.json(lab_data)

    st.markdown("<div style='height:0.4rem'></div>", unsafe_allow_html=True)

    if st.button("🔍 Analyse Report", disabled=bool(key_error)):
        if key_error:
            st.stop()

        graph = build_graph()
        try:
            with st.spinner("Running AI agents — explanations, flags, research, safety…"):
                result = graph.invoke({"lab_data": lab_data})
        except Exception as e:
            err = str(e).lower()
            if "429" in err or "rate limit" in err or "quota" in err:
                st.error("**Groq rate limit hit.** Wait a few seconds and click **Analyse Report** again.")
                st.stop()
            if "api key" in err or "401" in err or "403" in err:
                st.error(
                    "Groq rejected your API key. Update `GROQ_API_KEY_MEDICAL` in `.env`."
                )
                st.stop()
            raise

        report = result.get("final_report", {})
        if "error" in report:
            st.error(f"Agent error: {report['error']}")
            st.json(report.get("raw", {}))
            st.stop()

        # ── Explanations ──────────────────────────────────────────────────────
        st.markdown(
            '<div class="section-head"><span class="dot" style="background:#F06FA0"></span>Plain English Explanations</div>',
            unsafe_allow_html=True,
        )
        for item in report.get("explanations", []):
            st.markdown(
                f"""
                <div class="explain-card">
                    <div class="explain-test">{item['test']}</div>
                    <p class="explain-text">{item['plain_english']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Flags ─────────────────────────────────────────────────────────────
        flags = report.get("flags", [])
        counts = {"Normal": 0, "Watch": 0, "High priority": 0, "Critical": 0}
        for f in flags:
            sev = f.get("severity", "Normal")
            counts[sev] = counts.get(sev, 0) + 1

        st.markdown(
            f"""
            <div class="section-head">
                <span class="dot" style="background:#FFEABB"></span>
                Severity Flags
                <span style="margin-left:auto;display:flex;gap:0.6rem;font-size:0.75rem;font-weight:500">
                    <span style="color:#15803d">● {counts['Normal']} Normal</span>
                    <span style="color:#a16207">● {counts['Watch']} Watch</span>
                    <span style="color:#c2410c">● {counts['High priority']} High</span>
                    <span style="color:#be185d">● {counts['Critical']} Critical</span>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        chip_map = {
            "Normal": "chip-normal",
            "Watch": "chip-watch",
            "High priority": "chip-high",
            "Critical": "chip-critical",
        }
        for item in flags:
            sev = item.get("severity", "Normal")
            st.markdown(
                f"""
                <div class="flag-row">
                    <span class="severity-chip {chip_map.get(sev, 'chip-normal')}">{sev}</span>
                    <div>
                        <div class="flag-test">{item['test']}</div>
                        <div class="flag-reason">{item['reason']}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Doctor questions ──────────────────────────────────────────────────
        st.markdown(
            '<div class="section-head"><span class="dot" style="background:#3b82f6"></span>Questions to Ask Your Doctor</div>',
            unsafe_allow_html=True,
        )
        for i, q in enumerate(report.get("questions", []), 1):
            st.markdown(
                f"""
                <div class="q-card">
                    <div class="q-num">{i}</div>
                    <p class="q-text">{q['question']}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ── Disclaimer ────────────────────────────────────────────────────────
        st.markdown(
            f"""
            <div class="disclaimer">
                <span class="disclaimer-icon">⚠️</span>
                <span class="disclaimer-text">{report.get('disclaimer', '')}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.download_button(
            "⬇️ Download Full Report (JSON)",
            data=json.dumps(report, indent=2),
            file_name="mediscan_report.json",
            mime="application/json",
        )

# ── Universal dashboard pages ────────────────────────────────────────────────
if section == "Dashboard":
    st.markdown("### Dashboard")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Stored reports", sum(len(history_store.list_reports(p["patient_id"])) for p in patients))
    c2.metric("Detected values", len(st.session_state.lab_rows))
    c3.metric("Patient profiles", len(patients))
    c4.metric("Abnormal findings", sum(1 for r in st.session_state.lab_rows if r.get("status") in {"Low", "High", "Critical"}))

    if st.session_state.lab_rows:
        analysis = st.session_state.analysis or explain_lab_results(st.session_state.lab_rows)
        st.markdown("#### Latest processed report")
        st.write(analysis["summary"])
        if analysis["findings"]:
            for finding in analysis["findings"][:6]:
                st.warning(finding)
        st.markdown("#### Recommended follow-up")
        for question in analysis["question_suggestions"]:
            st.write(f"- {question}")
    else:
        st.info("Upload a report to begin document processing and view an actual patient-facing summary.")

elif section == "Upload Medical Report":
    st.markdown("### Upload Medical Report")
    st.caption("JPG, JPEG, PNG, text PDFs, scanned PDFs, image-based PDFs, and multi-page PDFs are supported.")

    profile_name = st.text_input("Patient profile name", value="Patient 1")
    profile_choice = st.selectbox("Patient profile", list(patient_names) if patient_names else ["Create profile in Patient Profile first"])
    report_date = st.date_input("Actual report date (if printed)", value=None)
    uploaded_files = st.file_uploader("Upload one or more documents", type=["jpg", "jpeg", "png", "pdf"], accept_multiple_files=True)

    if st.button("Process documents", disabled=not uploaded_files):
        st.session_state.documents = []
        all_rows = []
        progress = st.progress(0, text="Validating documents")

        for index, uploaded_file in enumerate(uploaded_files):
            try:
                content = uploaded_file.getvalue()
                validate_upload(uploaded_file.name, content)
                with st.spinner(f"Processing {uploaded_file.name}"):
                    result = process_document(uploaded_file.name, content)

                page_rows = [{"page_number": p.page_number, "text": p.text, "confidence": p.confidence} for p in result.pages]
                values = extract_structured_values(result.text, page_rows)
                all_rows.extend([value.model_dump() for value in values])
                st.session_state.documents.append({
                    "name": result.document_name,
                    "document_type": result.document_type,
                    "page_count": result.page_count,
                    "pages": page_rows,
                    "text": result.text,
                    "warnings": [p.warning for p in result.pages if p.warning],
                })

                with st.expander(f"Document preview: {uploaded_file.name}", expanded=False):
                    if uploaded_file.type and uploaded_file.type.startswith("image"):
                        st.image(content, caption=uploaded_file.name, use_container_width=True)
                    else:
                        st.write(f"Pages: {result.page_count}")
                    for page in result.pages:
                        st.markdown(f"**Page {page.page_number}** — `{page.extraction_method}` — confidence `{page.confidence:.2f}`")
                        if page.warning:
                            st.warning(page.warning)
            except Exception as exc:
                st.error(f"{uploaded_file.name}: {exc}")
            progress.progress((index + 1) / len(uploaded_files), text="Processing complete")

        st.session_state.lab_rows = all_rows
        st.session_state.analysis = explain_lab_results(all_rows, "Simple English")
        st.session_state.guidance = generate_guidance(all_rows, st.session_state.patient_profile)
        st.session_state.doctor_questions = generate_doctor_questions(all_rows)
        st.session_state.agent_report = None

        if all_rows:
            if key_error:
                st.session_state.agent_status = "AI explanations: Groq API key unavailable; showing validated local explanations only."
            else:
                try:
                    graph_result = build_graph().invoke({"lab_data": all_rows})
                    st.session_state.agent_report = graph_result.get("final_report", {})
                    if "error" in st.session_state.agent_report:
                        st.session_state.agent_status = "Groq analysis could not be generated safely."
                    else:
                        st.session_state.agent_status = "Groq and LangGraph analysis completed."
                except Exception as exc:
                    st.session_state.agent_status = f"Groq analysis unavailable: {exc}"

    if st.session_state.lab_rows:
        analysis = st.session_state.analysis or explain_lab_results(st.session_state.lab_rows)
        counts = analysis["counts"]
        st.markdown("### Medical Analysis Dashboard")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Parameters", len(st.session_state.lab_rows))
        c2.metric("Normal", counts["Normal"])
        c3.metric("Low", counts["Low"])
        c4.metric("High", counts["High"])
        c5.metric("Unclassified", counts["Unknown"])
        st.info(analysis["summary"])

        table_rows = [{
            "Test": row.get("test_name", "Unknown"),
            "Result": row.get("value", "Unavailable"),
            "Unit": row.get("unit", ""),
            "Reference Range": row.get("reference_range", "Unverified" if row.get("verification_needed") else "Unavailable"),
            "Status": "Verify range" if row.get("verification_needed") else row.get("status", "Unknown"),
            "Page": row.get("page_number", 1),
        } for row in st.session_state.lab_rows]
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        pie = go.Figure(go.Pie(
            labels=["Normal", "Low", "High", "Unclassified"],
            values=[counts["Normal"], counts["Low"], counts["High"], counts["Unknown"]],
            hole=0.52,
            marker=dict(colors=["#16a34a", "#f59e0b", "#dc2626", "#64748b"]),
        ))
        pie.update_layout(title="Laboratory parameter status", template="plotly_white")
        st.plotly_chart(pie, use_container_width=True)

        st.markdown("#### Simple explanations")
        for item in analysis["explanations"]:
            label = f"{item['test']} — {item['status']} — {item['value']} {item['unit']}"
            with st.expander(label, expanded=False):
                st.write(item["explanation"])
                if item.get("reference_range"):
                    st.caption(f"Report reference range: {item['reference_range']} | Source page: {item['page_number']}")

        if st.session_state.documents:
            with st.expander("View Original Extracted Text", expanded=False):
                for document in st.session_state.documents:
                    st.markdown(f"**{document['name']}**")
                    st.text(document["text"])

        if st.session_state.get("agent_status"):
            st.caption(st.session_state.agent_status)
        st.warning("This analysis is educational and is not a diagnosis. Discuss laboratory findings with a qualified healthcare professional.")

        st.success(f"{len(st.session_state.lab_rows)} structured lab values detected.")
        if st.button("Save processed report to medical history"):
            if profile_choice not in patient_names:
                st.error("Select or create a saved patient profile before saving this report.")
                st.stop()
            patient_id = patient_names[profile_choice]
            report_name = ", ".join(d["name"] for d in st.session_state.documents) or "Medical Report"
            history_store.save_report(
                patient_id,
                report_name,
                str(report_date) if report_date else None,
                ", ".join(sorted(set(d["document_type"] for d in st.session_state.documents))),
                st.session_state.lab_rows,
                {"documents": st.session_state.documents},
            )
            st.success("Report saved to local SQLite history.")

elif section == "Extracted Lab Results":
    st.markdown("### Extracted Lab Results")
    if not st.session_state.lab_rows:
        st.info("Upload and process a report first.")
    else:
        df = pd.DataFrame(st.session_state.lab_rows)
        columns = ["test_name", "value", "unit", "reference_range", "status", "page_number", "confidence", "original_text"]
        df = df[[column for column in columns if column in df.columns]]
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="lab_editor")
        st.session_state.lab_rows = edited.to_dict(orient="records")

        st.session_state.analysis = explain_lab_results(st.session_state.lab_rows, "Simple English")
        c1, c2, c3, c4 = st.columns(4)
        counts = st.session_state.analysis["counts"]
        c1.metric("Normal", counts["Normal"])
        c2.metric("Low", counts["Low"])
        c3.metric("High", counts["High"])
        c4.metric("Uncertain", counts["Unknown"])

        st.info(st.session_state.analysis["summary"])
        status = go.Figure(go.Pie(
            labels=["Normal", "Low", "High", "Unclassified"],
            values=[counts["Normal"], counts["Low"], counts["High"], counts["Unknown"]],
            hole=0.52,
            marker=dict(colors=["#15803d", "#d97706", "#dc2626", "#64748b"]),
        ))
        status.update_layout(title="Laboratory status overview", template="plotly_white", showlegend=False)
        st.plotly_chart(status, use_container_width=True)

        st.download_button("Download JSON", json.dumps(st.session_state.lab_rows, indent=2), "lab_results.json", "application/json")
        st.download_button("Download CSV", edited.to_csv(index=False), "lab_results.csv", "text/csv")

elif section == "Medical Report Explanation":
    st.markdown("### Medical Report Analysis")
    if not st.session_state.lab_rows:
        st.info("Upload and process a report first.")
    else:
        mode = st.radio("Explanation mode", ["Simple English", "Detailed Medical Explanation"], horizontal=True)
        analysis = explain_lab_results(st.session_state.lab_rows, mode)
        st.session_state.analysis = analysis
        guidance = generate_guidance(st.session_state.lab_rows, st.session_state.patient_profile)
        st.session_state.guidance = guidance
        questions = generate_doctor_questions(st.session_state.lab_rows)
        st.session_state.doctor_questions = questions

        tabs = st.tabs(["Overview", "Lab Results", "Simple Explanations", "Food & Nutrition", "What Should I Do Next?", "Questions For Your Doctor", "Original Text"])

        with tabs[0]:
            counts = analysis["counts"]
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Normal", counts["Normal"])
            c2.metric("Low", counts["Low"])
            c3.metric("High", counts["High"])
            c4.metric("Unclassified", counts["Unknown"])
            st.markdown("#### Overall summary")
            st.write(analysis["summary"])
            for finding in analysis["findings"]:
                st.warning(finding)

        with tabs[1]:
            rows = [{"Test": r.get("test_name"), "Result": r.get("value"), "Unit": r.get("unit"), "Reference Range": r.get("reference_range") or "Unavailable", "Status": "Verify range" if r.get("verification_needed") else r.get("status"), "Page": r.get("page_number")} for r in st.session_state.lab_rows]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        with tabs[2]:
            for item in analysis["explanations"]:
                with st.expander(f"{item['test']} — {item['status']} — {item['value']} {item['unit']}", expanded=False):
                    st.write(item["explanation"])
                    st.markdown(f"**Page:** {item['page_number']}  |  **Reference:** {item['reference_range'] or 'Unavailable'}")

        with tabs[3]:
            if guidance["nutrition"]:
                for item in guidance["nutrition"]:
                    st.markdown(f"#### {item['title']}")
                    st.caption(f"Relevant finding: {item['test']} — {item['status']}")
                    for food in item["foods"]:
                        st.write(f"- {food}")
                    st.info(item["why"])
            else:
                st.info("No patient-specific food suggestion is supported by the currently extracted findings. General balanced nutrition guidance is safer until additional context is available.")

        with tabs[4]:
            next_steps = guidance["next_steps"]
            st.markdown("#### General precautions")
            for item in next_steps["precautions"]:
                st.write(f"- {item}")
            st.markdown("#### Report-related considerations")
            for item in next_steps["considerations"]:
                st.write(f"- {item}")
            if next_steps["restrictions"]:
                st.markdown("#### Profile considerations")
                for item in next_steps["restrictions"]:
                    st.warning(item)
            st.error(next_steps["urgent_warning"])

        with tabs[5]:
            question_text = "\n".join(f"{index}. {question}" for index, question in enumerate(questions, 1))
            for question in questions:
                st.markdown(f"<div class='q-card'><p class='q-text'>{question}</p></div>", unsafe_allow_html=True)
            st.download_button("Download questions as text", question_text, "mediscan_doctor_questions.txt", "text/plain")

        with tabs[6]:
            for document in st.session_state.documents:
                st.markdown(f"**{document['name']}**")
                st.text(document["text"])

        patient_name = st.text_input("Patient/profile name for PDF", value=st.session_state.patient_profile.get("name") or "Patient")
        report_name = ", ".join(d["name"] for d in st.session_state.documents) if st.session_state.documents else "Medical Report"
        pdf_bytes = generate_summary_pdf(patient_name, report_name, st.session_state.lab_rows, analysis, guidance, questions)
        st.download_button("Download comprehensive PDF summary", pdf_bytes, "mediscan_report_summary.pdf", "application/pdf")

elif section == "Visual Analytics":
    st.markdown("### Visual Analytics")
    if not st.session_state.lab_rows:
        st.info("Upload and process a report first.")
    else:
        counts = st.session_state.analysis["counts"] if st.session_state.analysis else explain_lab_results(st.session_state.lab_rows)["counts"]
        status_fig = go.Figure(go.Pie(
            labels=["Normal", "Low", "High", "Unclassified"],
            values=[counts["Normal"], counts["Low"], counts["High"], counts["Unknown"]],
            hole=0.52,
            marker=dict(colors=["#16a34a", "#f59e0b", "#dc2626", "#64748b"]),
        ))
        status_fig.update_layout(title="Lab status distribution", template="plotly_white")
        st.plotly_chart(status_fig, use_container_width=True)

        options = [row for row in st.session_state.lab_rows if row.get("value") is not None]
        if not options:
            st.info("No numeric values are available for reference-range charts.")
        else:
            names = [row["test_name"] for row in options]
            selected = st.selectbox("Select a parameter", names)
            row = next(row for row in options if row["test_name"] == selected)
            reference = str(row.get("reference_range", ""))
            import re
            match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)", reference)

            value = float(row["value"])
            unit = row.get("unit", "")
            if match:
                lower, upper = map(float, match.groups())
                pad = max((upper - lower) * 0.25, abs(value) * 0.1, 1.0)
                chart_min = min(lower, value) - pad
                chart_max = max(upper, value) + pad
                fig = go.Figure()
                fig.add_trace(go.Bar(x=[lower, upper - lower], y=[selected], orientation="h", marker_color="#dcfce7", name="Reference range", hovertemplate="Reference %{x}<extra></extra>"))
                fig.add_trace(go.Scatter(x=[value], y=[selected], mode="markers", marker=dict(size=18, color="#be185d", symbol="diamond"), name="Measured value", hovertemplate="Value %{x} " + unit + "<extra></extra>"))
                fig.update_layout(title=f"{selected}: measured value within report reference range", xaxis=dict(range=[chart_min, chart_max], title=f"Value ({unit})"), yaxis=dict(showticklabels=False), template="plotly_white", barmode="overlay")
                st.plotly_chart(fig, use_container_width=True)
            else:
                fig = go.Figure(go.Indicator(mode="number+delta", value=value, number={"suffix": f" {unit}"}, title={"text": f"{selected} — reference range unavailable"}))
                st.plotly_chart(fig, use_container_width=True)

elif section == "Medical History":
    st.markdown("### Medical History")
    if not patients:
        st.info("Create a patient profile by saving an uploaded report.")
    else:
        patient_name = st.selectbox("Patient", list(patient_names), key="history_patient")
        reports = history_store.list_reports(patient_names[patient_name])
        if not reports:
            st.info("No reports stored for this patient.")
        else:
            for report in reports:
                c1, c2 = st.columns([5, 1])
                c1.markdown(f"**{report['report_name']}**  \nUploaded {report['upload_date']} | Report date {report['report_date'] or 'Unavailable'} | {report['processing_status']}")
                if c2.button("Delete", key=f"delete_{report['report_id']}"):
                    history_store.delete_report(report["report_id"])
                    st.rerun()

            if len(reports) == 1:
                st.info("Only one report is stored. A historical trend requires multiple reports; an individual reference-range view is available in Visual Analytics.")

            parameters = sorted({p["test_name"] for r in reports for p in r["extracted_parameters"]})
            parameter = st.selectbox("Parameter trend", parameters)
            points = []
            for report in reversed(reports):
                date = report["report_date"] or report["upload_date"][:10]
                for value in report["extracted_parameters"]:
                    if value["test_name"] == parameter:
                        points.append((date, value["value"], value["status"]))
            if points:
                fig = go.Figure(go.Scatter(x=[p[0] for p in points], y=[p[1] for p in points], mode="lines+markers", text=[p[2] for p in points], hovertemplate="Date %{x}<br>Value %{y}<br>Status %{text}<extra></extra>"))
                fig.update_layout(title=f"{parameter} trend", xaxis_title="Report date", yaxis_title="Measured value", template="plotly_white")
                st.plotly_chart(fig, use_container_width=True)

elif section == "Compare Reports":
    st.markdown("### Compare Reports")
    if not patients:
        st.info("Create a patient profile and save at least two reports first.")
    else:
        patient_name = st.selectbox("Patient", list(patient_names), key="compare_patient")
        reports = history_store.list_reports(patient_names[patient_name])
        if len(reports) < 2:
            st.info("At least two reports are required for comparison.")
        else:
            choices = {f"{r['report_name']} ({r['report_date'] or r['upload_date'][:10]})": r for r in reports}
            previous_choice = st.selectbox("Previous report", list(choices), key="previous_report")
            remaining = [name for name in choices if name != previous_choice]
            current_choice = st.selectbox("Current report", remaining, key="current_report")
            comparison = compare_reports(choices[previous_choice]["extracted_parameters"], choices[current_choice]["extracted_parameters"])
            if comparison:
                st.dataframe(pd.DataFrame(comparison), use_container_width=True)
                summary = []
                for row in comparison:
                    if row["comparison_available"]:
                        summary.append(f"{row['parameter']} changed {row['absolute_difference']} {row['current_unit']} ({row['percentage_difference']}%) in the selected reports. This trend is not by itself diagnostic.")
                    else:
                        summary.append(f"{row['parameter']} comparison is unavailable because units or values are missing or incompatible.")
                st.markdown("#### Comparison summary")
                st.write(" ".join(summary))
            else:
                st.info("No compatible common parameters were found.")

elif section == "AI Medical Assistant":
    st.markdown("### AI Medical Assistant")
    if not st.session_state.lab_rows:
        st.info("Upload and validate extracted lab values before asking questions.")
    else:
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        question = st.chat_input("Ask about a test, the report, or what to discuss with your doctor")
        if question:
            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.chat_message("user"):
                st.write(question)

            if key_error:
                answer = "AI chat is unavailable because a valid Groq API key is not configured. You can still use the report explanations and visual analytics."
            else:
                context_rows = json.dumps(st.session_state.lab_rows, ensure_ascii=False)
                prompt = f"""You are a conservative medical report assistant.
Use ONLY the following validated extracted laboratory values as report context:
{context_rows}

Conversation question: {question}

Rules:
- Explain the report in ordinary, patient-friendly language.
- Never invent values or reference ranges that are not in the context.
- Never diagnose or prescribe medication.
- Distinguish uncertainty from facts.
- Suggest questions for a qualified healthcare professional.
- If a historical comparison was not provided, say that no historical trend is available.
Return concise Markdown without a diagnosis."""
                try:
                    answer = invoke_llm(prompt)
                except Exception as exc:
                    answer = f"The AI assistant could not answer this question: {exc}"

            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            with st.chat_message("assistant"):
                st.write(answer)

        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()

        st.download_button("Download chatbot context JSON", json.dumps(st.session_state.lab_rows, indent=2), "medical_chat_context.json", "application/json")

elif section == "Patient Profile":
    st.markdown("### Patient Profile")

    profiles = patient_repository.list_profiles()
    profile_options = {f"{profile['profile_name']} (ID {profile['id']})": profile['id'] for profile in profiles}

    col_selector, col_create = st.columns([3, 1])
    with col_selector:
        if profiles:
            active_id = st.session_state.active_patient_id
            default_name = next((name for name, profile_id in profile_options.items() if profile_id == active_id), list(profile_options)[0])
            selected_name = st.selectbox("Saved patient profiles", list(profile_options), index=list(profile_options).index(default_name))
            selected_id = profile_options[selected_name]
        else:
            selected_id = None
            st.info("No saved patient profiles yet.")

    with col_create:
        if st.button("CREATE NEW PROFILE"):
            st.session_state.active_patient_id = None
            st.session_state.creating_profile = True
            st.session_state.patient_profile = {"name": "", "age": None, "sex": "", "diabetes": False,
                                                "kidney_disease": False, "pregnancy": False,
                                                "allergies": "", "dietary_restrictions": ""}
            st.rerun()

    if not st.session_state.creating_profile and selected_id is not None and st.session_state.active_patient_id != selected_id:
        saved = patient_repository.get_profile(selected_id)
        if saved:
            st.session_state.active_patient_id = selected_id
            st.session_state.patient_profile = {
                "name": saved["profile_name"],
                "age": saved["age"],
                "sex": saved["sex"],
                "diabetes": saved["diabetes"],
                "kidney_disease": saved["kidney_disease"],
                "pregnancy": saved["pregnancy"],
                "allergies": saved["food_allergies"],
                "dietary_restrictions": saved["dietary_restrictions"],
            }

    profile = st.session_state.patient_profile
    st.markdown(f"**Currently selected:** {profile.get('name') or 'Unsaved new profile'}")

    profile["name"] = st.text_input("Profile name", value=profile.get("name") or "")
    profile["age"] = st.number_input("Age", min_value=0, max_value=120,
                                     value=int(profile.get("age") or 0)) or None
    sex_options = ["", "Female", "Male", "Other/Unspecified"]
    profile["sex"] = st.selectbox("Sex", sex_options,
                                   index=sex_options.index(profile.get("sex") or ""))
    profile["diabetes"] = st.checkbox("Diabetes", value=profile.get("diabetes", False))
    profile["kidney_disease"] = st.checkbox("Kidney disease or kidney restriction",
                                             value=profile.get("kidney_disease", False))
    profile["pregnancy"] = st.checkbox("Pregnancy", value=profile.get("pregnancy", False))
    profile["allergies"] = st.text_input("Food allergies", value=profile.get("allergies") or "")
    profile["dietary_restrictions"] = st.text_input("Dietary restrictions",
                                                    value=profile.get("dietary_restrictions") or "")

    save_col, delete_col = st.columns(2)
    with save_col:
        if st.button("SAVE PROFILE", type="primary"):
            try:
                saved = patient_repository.save_profile(
                    st.session_state.active_patient_id,
                    profile["name"], profile["age"], profile["sex"],
                    profile["diabetes"], profile["kidney_disease"], profile["pregnancy"],
                    profile["allergies"], profile["dietary_restrictions"],
                )
                st.session_state.active_patient_id = saved["id"]
                st.session_state.creating_profile = False
                st.session_state.patient_profile = {
                    "name": saved["profile_name"], "age": saved["age"], "sex": saved["sex"],
                    "diabetes": saved["diabetes"], "kidney_disease": saved["kidney_disease"],
                    "pregnancy": saved["pregnancy"], "allergies": saved["food_allergies"],
                    "dietary_restrictions": saved["dietary_restrictions"],
                }
                st.success(f"Profile '{saved['profile_name']}' saved permanently to the SQLite database.")
            except ProfileValidationError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"Profile could not be saved to SQLite: {exc}")

    with delete_col:
        if st.session_state.active_patient_id:
            confirm_delete = st.checkbox("Confirm profile deletion")
            if st.button("DELETE PROFILE", disabled=not confirm_delete):
                try:
                    patient_repository.delete_profile(st.session_state.active_patient_id)
                    st.session_state.active_patient_id = None
                    st.session_state.creating_profile = False
                    st.session_state.patient_profile = {"name": "", "age": None, "sex": "", "diabetes": False,
                                                        "kidney_disease": False, "pregnancy": False,
                                                        "allergies": "", "dietary_restrictions": ""}
                    st.success("Profile deleted from the SQLite database.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Profile could not be deleted: {exc}")

elif section == "Settings":
    st.markdown("### Settings")
    st.checkbox("Use simple explanations by default", value=True)
    st.checkbox("Show OCR uncertainty warnings", value=True)
    st.checkbox("Show local educational guidance when AI is unavailable", value=True)
    st.markdown("#### Privacy")
    st.info("Reports are stored locally in SQLite for this prototype. Use Delete in My Medical Reports to remove a saved report. No report contents are intentionally logged.")
    if st.button("Clear current session data"):
        st.session_state.lab_rows = []
        st.session_state.documents = []
        st.session_state.agent_report = None
        st.session_state.analysis = None
        st.session_state.guidance = None
        st.session_state.doctor_questions = []
        st.session_state.chat_history = []
        st.success("Current report and chat session cleared.")