# Healthcare Intelligent Health Literacy Assistant

A RAG-based application that answers health questions exclusively from verified WHO medical documents. Every response includes citations, and the system refuses to answer when information is unavailable.

## Tech Stack

- **Backend:** FastAPI + LangChain + LangGraph
- **Frontend:** React + TypeScript + Vite + Tailwind CSS
- **LLM:** Ollama (local, no data leaves the server)
- **Vector DB:** ChromaDB
- **Database:** PostgreSQL
- **Embeddings:** BGE (BAAI/bge-small-en-v1.5)

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

# 3. Setup PostgreSQL database
# Create database: healthcare_db
# Update .env with your credentials

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
uvicorn app.main:app --host 0.0.0.0 --port 8003
```

### Terminal 3 — Start Frontend (React)
```bash
cd frontend
npm run dev
```

### Access
- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8003
- **API Docs:** http://localhost:8003/docs

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
│   │   ├── chat_service.py       # Main orchestrator
│   │   ├── rag_service.py        # RAG pipeline (ChromaDB + LLM)
│   │   ├── guardrails_service.py # PII sanitization + emergency detection
│   │   ├── jargon_simplifier.py  # Medical jargon → plain language
│   │   ├── ingestion_service.py  # PDF parsing → ChromaDB indexing
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

- **RAG from verified WHO documents only** — no hallucination from general knowledge
- **Citation engine** — every answer shows source PDF, page number, section
- **Emergency detection** — heart attack, suicide, overdose → redirects to 112/108
- **PII sanitization** — email, phone, SSN removed before processing
- **Jargon simplifier** — clinical language rewritten in plain English
- **Simplification validation** — cosine similarity ≥ 0.85 ensures accuracy
- **Document validation pipeline** — PDF-only, SHA-256 hash, trusted source whitelist, admin approval
- **RLHF feedback** — thumbs up/down + corrections build a Golden Dataset
- **Voice input** — ask questions using microphone (Web Speech API)
- **PostgreSQL** — conversations, feedback, document records persisted
- **Local LLM** — Ollama runs on-device, no data transmitted externally
