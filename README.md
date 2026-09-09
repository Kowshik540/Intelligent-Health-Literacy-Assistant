# Healthcare Intelligent Health Literacy Assistant

A RAG-based health assistant that answers from verified WHO medical documents with
citations, backed by a **deterministic clinical safety layer**. The core design
idea: the Python code makes every math and safety decision (so it is predictable),
and the LLM only turns verified facts into clear, plain-language answers. This
prevents dangerous mistakes such as mislabeling a normal blood pressure as
hypertension or downplaying an emergency.

## Tech Stack

- **Backend:** FastAPI + LangChain
- **Frontend:** React + TypeScript + Vite
- **LLM:** Ollama (local, no data leaves the server)
- **Vector DB:** ChromaDB
- **Database:** PostgreSQL (or SQLite for zero-setup local runs)
- **Embeddings:** BGE (BAAI/bge-small-en-v1.5)

## How it works (request pipeline)

Every message flows through `ChatService` in a fixed order:

1. **Guardrails** — emergency phrases + PII removal (`guardrails_service.py`)
2. **Triage** — deterministic red-flag / acuity check (`clinical_triage_service.py`)
3. **Biometrics** — classifies BP / HR / SpO2 / temp / glucose by fixed clinical
   thresholds (`biometric_service.py`)
4. **Clarification** — asks one focused follow-up for non-emergencies
   (`clarification_service.py`)
5. **RAG** — retrieve from ChromaDB + generate a cited answer (`rag_service.py`)
6. **Simplify** — plain-language rewrite (`jargon_simplifier.py`)
7. **Verify** — blocks answers that contradict the facts or downplay acuity
   (`output_verification_service.py`)
8. **Drug interactions** — flags dangerous combinations (`drug_interaction_service.py`)
9. **Persist** — save messages and return the answer with citations

Emergencies (e.g. chest pain, stroke signs, severe pain, headache + fever) are
intercepted at the triage step and answered immediately with **no follow-up
questions**.

## Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Ollama (https://ollama.ai)

## Setup

```bash
# 1. Clone and install Python dependencies
cd MEDICAL-RAG-CHATBOT
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt

# 2. Install frontend dependencies
cd frontend
npm install
cd ..

# 3. Configure the database
# Copy .env.example to .env. It defaults to a local SQLite file (zero setup).
# To use PostgreSQL: create a database named healthcare_db and set
#   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/healthcare_db
# (URL-encode special characters in the password, e.g. # -> %23).
# Tables are created automatically on first startup — no manual migration needed.
copy .env.example .env           # Windows  (cp on macOS/Linux)

# 4. Pull the LLM model
ollama pull qwen2:1.5b

# 5. Seed documents into ChromaDB
python seed_documents.py
```

## Running the Application

### Terminal 1 — Start Ollama (LLM Server)
```bash
ollama serve
```

### Terminal 2 — Start Backend (FastAPI)
```bash
venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Terminal 3 — Start Frontend (React)
```bash
cd frontend
npm run dev
```

### Access
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## Running Tests

```bash
venv\Scripts\activate
python tests/test_all.py
```

## Project Structure

```
MEDICAL-RAG-CHATBOT/
├── app/                          # Backend application
│   ├── main.py                   # FastAPI entry point
│   ├── core/                     # Config and database setup
│   │   ├── config.py             # Environment settings (Pydantic)
│   │   └── database.py           # Async SQLAlchemy + PostgreSQL pooling
│   ├── models/                   # ORM models (SQLAlchemy)
│   │   ├── user.py               # User accounts
│   │   ├── conversation.py       # Conversations and messages
│   │   ├── document.py           # Ingested medical documents
│   │   └── feedback.py           # RLHF feedback (Golden Dataset)
│   ├── schemas/                  # Request/Response validation (Pydantic)
│   ├── repositories/             # Database access layer
│   ├── services/                 # Business logic
│   │   ├── chat_service.py       # Main orchestrator (runs the full pipeline)
│   │   ├── rag_service.py        # RAG pipeline (ChromaDB + LLM)
│   │   ├── llm_factory.py        # Builds LLM / embeddings / vector store
│   │   ├── guardrails_service.py # PII sanitization + emergency detection
│   │   ├── clinical_triage_service.py     # Red-flag / acuity detection
│   │   ├── biometric_service.py           # Vital-sign classification (rules)
│   │   ├── output_verification_service.py # Blocks contradictory answers
│   │   ├── drug_interaction_service.py    # High-risk drug interaction checks
│   │   ├── clarification_service.py       # One-question-at-a-time follow-ups
│   │   ├── jargon_simplifier.py  # Medical jargon → plain language
│   │   ├── ingestion_service.py  # PDF/text parsing → ChromaDB indexing
│   │   └── document_validation_service.py  # Source verification
│   └── api/v1/routes/            # HTTP endpoints
│       ├── chat.py               # POST /api/v1/chat
│       ├── documents.py          # POST /api/v1/ingest
│       ├── feedback.py           # POST /api/v1/feedback
│       └── health.py             # GET /api/v1/health
├── frontend/                     # React frontend
│   └── src/App.tsx               # Chat UI with voice input
├── alembic/                      # Database migrations
├── tests/                        # Automated test suite
├── sample_docs/                  # Source WHO PDF documents
├── data/                         # Compiled medical guidelines
├── requirements.txt              # Python dependencies
└── .env.example                  # Environment variable template
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/chat/ | Send a health question, get cited answer |
| POST | /api/v1/ingest | Upload a medical PDF for validation |
| POST | /api/v1/ingest/approve/{id} | Admin approves document for indexing |
| GET | /api/v1/sources/{id} | Get document metadata |
| POST | /api/v1/feedback/ | Submit thumbs up/down on a response |
| GET | /api/v1/feedback/golden-dataset | Get corrections for fine-tuning |
| GET | /api/v1/health | Service health check |

## Key Features

- **RAG from verified WHO documents** — answers grounded in the document library,
  with a clearly-labelled general-knowledge fallback (no fake citations)
- **Citation engine** — every document-backed answer shows source PDF, page, section
- **Deterministic clinical triage** — chest pain, stroke signs, severe pain (≥7/10),
  "worst headache of my life", headache + fever (meningitis), acute abdomen, and
  breathing trouble are intercepted as emergencies with **zero follow-up questions**
- **Deterministic biometrics** — BP / HR / SpO2 / temperature / glucose classified by
  fixed clinical thresholds in code, so e.g. 110/60 is always "normal", never
  hypertension
- **Output verification** — the generated answer is blocked/regenerated if it
  contradicts a vital-sign fact or downplays a serious symptom
- **Drug interaction checks** — flags high-risk combinations (e.g. ibuprofen +
  lisinopril) and suggests a safer alternative
- **Multi-turn memory** — vitals/symptoms from earlier turns are carried forward
- **Emergency detection + PII sanitization** — helpline redirect; email/phone/SSN
  removed before processing
- **Jargon simplifier** — clinical language rewritten in plain English
- **Document validation pipeline** — PDF-only, SHA-256 hash, trusted-source
  whitelist, admin approval
- **RLHF feedback** — thumbs up/down + corrections build a Golden Dataset
- **Voice input** — ask questions using the microphone (Web Speech API)
- **PostgreSQL / SQLite** — conversations, feedback, and document records persisted
- **Local LLM** — Ollama runs on-device, no data transmitted externally

## Automated Tests

`python tests/test_all.py` runs 26 checks covering PII redaction, emergency
detection, document validation, retrieval, generation, the database, and the API.

## Presentation / Docs

- `docs/PRESENTATION_GUIDE.md` — module walkthrough for the demo
- `docs/VIDEO_SPEAKING_PARTS.txt` — per-person speaking parts for the video
