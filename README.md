# 🩺 MediScan AI — Medical Report Simplifier

> Upload JPG, JPEG, PNG, text PDFs, scanned PDFs, and multi-page PDFs to review structured lab values, medical history, comparisons, and a plain-English AI summary.

---

## 📸 Demo

![MediScan AI Screenshot](assets/screenshot.png)

---

## ✨ Features

- 📄 **Universal Document Scanner** — Native PyMuPDF extraction and Tesseract/OpenCV OCR for JPG, JPEG, PNG, scanned PDFs, and multi-page PDFs
- 🧠 **Multi-Agent AI Pipeline** — 4 specialized agents powered by LangGraph
- 💬 **Plain English Explanations** — Every test value explained in simple language
- 🚦 **Severity Flagging** — Color-coded: Normal, Watch, High Priority, Critical
- ❓ **Doctor Questions** — Auto-generated questions to bring to your next appointment
- � **Structured Lab Extraction** — Pydantic validation, printed reference ranges, page numbers, confidence, statuses, and manual correction
- 📈 **Medical History** — SQLite-backed report storage, deletion, Plotly trends, and report comparison
- 🔒 **Privacy Controls** — Local history storage and deletion; report contents are not logged
- ⚡ **Fast** — Groq LLM delivers results in ~10 seconds
- 📥 **Downloadable Report** — Export full analysis as JSON

---

## 🏗️ Architecture

```
PDF Upload
    │
    ▼
PDF Parser (PyMuPDF)
    │
    ▼
RAG Context Retrieval (ChromaDB + HuggingFace Embeddings)
    │
    ▼
┌─────────────────────────────────────┐
│         LangGraph Pipeline          │
│                                     │
│  ┌─────────────┐ ┌───────────────┐  │
│  │  Explainer  │ │   Flagging    │  │
│  │   Agent     │ │    Agent      │  │
│  └──────┬──────┘ └──────┬────────┘  │
│         └───────┬────────┘          │
│                 ▼                   │
│         ┌──────────────┐            │
│         │   Research   │            │
│         │    Agent     │            │
│         └──────┬───────┘            │
│                ▼                    │
│         ┌──────────────┐            │
│         │    Safety    │            │
│         │    Agent     │            │
│         └──────┬───────┘            │
└────────────────┼────────────────────┘
                 ▼
         Final Patient Report
```

---

## 🧰 Tech Stack

| Layer | Tool |
|---|---|
| LLM | Groq API (`llama-3.3-70b-versatile`) |
| Agent Framework | LangGraph |
| RAG / Vector DB | ChromaDB |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` |
| Document/OCR | PyMuPDF, Pillow, OpenCV, Tesseract |
| History/Charts | SQLite, Plotly |
| Frontend | Streamlit |
| Language | Python 3.10+ |

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/NehasriMadala/MediScan-AI.git
cd MediScan-AI
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR (required for scanned PDFs and photographs)

**Windows:**

```powershell
winget install --exact --id UB-Mannheim.TesseractOCR
```

After installation, restart VS Code/Streamlit. The app checks `C:\Program Files\Tesseract-OCR\tesseract.exe` automatically.

**macOS:** `brew install tesseract`

**Ubuntu/Debian:** `sudo apt install tesseract-ocr`

For a custom executable path, set `TESSERACT_CMD` in `.env`.

### 5. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=your_groq_api_key_here
```

Get a free key at [console.groq.com](https://console.groq.com) — no credit card needed.

### 6. Build the RAG knowledge base (run once)

```bash
python build_rag.py
```

### 7. Run the app

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

---

## 📁 Project Structure

```
medical-report-agent/
├── .streamlit/
│   └── config.toml         # Streamlit theme config
├── app.py                  # Streamlit frontend
├── agents.py               # LLM agent functions (Groq)
├── graph.py                # LangGraph multi-agent pipeline
├── pdf_parser.py           # Backward-compatible PDF extraction API
├── utils/
│   ├── document_processor.py # Upload validation and PDF/image routing
│   ├── lab_extractor.py      # Pydantic lab extraction and status classification
│   ├── history_store.py      # SQLite patient and report storage
│   └── report_comparison.py  # Compatible unit and trend comparison
├── tests/
│   └── test_core.py          # Synthetic document, lab, and history tests
├── rag_setup.py            # ChromaDB vector store setup
├── build_rag.py            # One-time RAG build script
├── schemas.py              # Pydantic output schemas
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
└── README.md
```

---

## 🤖 Agent Pipeline

| Agent | Role |
|---|---|
| **Explainer** | Translates each lab value into one plain-English sentence |
| **Flagging** | Assigns severity: Normal / Watch / High Priority / Critical |
| **Research** | Generates 3–5 smart questions to ask your doctor |
| **Safety** | Reviews output for diagnostic language; adds disclaimer |

---

## ⚙️ Requirements

Create a `requirements.txt`:

```
streamlit
langchain
langchain-groq
langchain-community
langgraph
chromadb
sentence-transformers
pymupdf
python-dotenv
pydantic
```

---

## 🔑 Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key from [console.groq.com](https://console.groq.com) |

---

## ⚠️ Disclaimer

This tool is for **educational purposes only** and does not constitute medical advice. Always consult a qualified healthcare provider for interpretation of lab results and medical decisions.

---

## 🙌 Acknowledgements

- [Groq](https://groq.com) — Ultra-fast LLM inference
- [LangGraph](https://github.com/langchain-ai/langgraph) — Multi-agent orchestration
- [ChromaDB](https://www.trychroma.com) — Local vector database
- [Streamlit](https://streamlit.io) — Rapid UI development

---

## 📄 License

MIT License — feel free to use, modify, and distribute.
