# PROJECT DOCUMENTATION

## Intelligent Health Literacy Assistant

A RAG-based application that answers health questions only from verified medical documents

**Project 1 — Healthcare Domain**

**Status:** Phase 1 Complete, Phase 2 In Progress

**Team Members**
- Bhavya Konagala
- Bachina Manogna
- A Naga Laxmi
- Kowshik Thota
- K. Dharani Thanuja

**Document Version:** 1.0
**Last Updated:** August 19, 2026

---

## Table of Contents

1. Executive Summary & Objectives
2. System Architecture
3. Technical Specifications
4. Development Progress
5. Module Descriptions
6. How to Run
7. Next Steps

---

## 1. Executive Summary & Objectives

### 1.1 Problem Statement

People often search online for health information, but results are frequently confusing, contradictory, or unreliable. Medical jargon is difficult to understand, and there is no clear way to verify the source or accuracy of the information. This can lead to risky health decisions.

We are building a RAG-based application that provides clear, evidence-based medical answers only from verified sources such as WHO guidelines, government protocols, and certified journals. Every response includes citations, and the system refrains from answering when information is unavailable.

### 1.2 Project Scope

**In-Scope**

- A RAG-based application that ingests medical PDFs and answers questions using only that content
- A citation system that shows the source PDF and page number behind every answer
- An explicit "I don't know" response when the retrieved content doesn't answer the question
- Basic handling for emergency-sounding queries (redirects to 112/108)
- PII sanitization so personal data never reaches the LLM

**Out-of-Scope**

- No integration with hospital systems or electronic health records
- No diagnosis, prescriptions, or treatment recommendations

---

## 2. System Architecture

### 2.1 High-Level Architecture

The system has three main layers:

- **Backend (FastAPI)** — handles API requests, coordinates the pipeline
- **AI Layer (LangChain + Ollama)** — retrieves documents, generates cited answers
- **Data Layer (ChromaDB + PostgreSQL)** — stores document vectors and application data

### 2.2 Data Ingestion Pipeline

How medical PDFs become searchable knowledge:

1. **PDF Parsing** — pdfplumber extracts text while preserving page boundaries
2. **Chunking** — RecursiveCharacterTextSplitter splits text into ~1000 char chunks with 200 overlap
3. **Metadata Tagging** — each chunk tagged with source filename, page number, section header
4. **Embedding** — BGE model (BAAI/bge-small-en-v1.5) converts chunks to 384-dimensional vectors
5. **Storage** — vectors and metadata stored in ChromaDB for fast similarity search

### 2.3 RAG Pipeline (Phase 2)

How a user's question gets answered:

1. User submits a health question
2. PII sanitization removes any personal information
3. Emergency detection checks for crisis language — if matched, returns 112/108 guidance
4. Question is embedded using BGE model
5. ChromaDB is searched for the 3 most similar document chunks
6. If no chunks pass the relevance threshold (0.45) → system refuses to answer
7. Relevant chunks are passed to Ollama LLM with strict citation instructions
8. LLM generates an answer using only the provided document content
9. Answer with citations is returned

---

## 3. Technical Specifications

### 3.1 Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Backend | FastAPI | HTTP server, request handling |
| Database | PostgreSQL | Stores document records, audit logs |
| Vector DB | ChromaDB | Stores document embeddings for semantic search |
| Embeddings | BGE (bge-small-en-v1.5) | Converts text to vectors |
| LLM | Ollama (qwen2:1.5b) | Generates answers from retrieved context |
| PDF Processing | pdfplumber | Extracts text from medical PDFs |
| Text Splitting | LangChain | Section-aware chunking |
| ORM | SQLAlchemy (async) | Database access with connection pooling |

### 3.2 API Endpoints

| Endpoint | Method | Description | Phase |
|----------|--------|-------------|-------|
| /api/v1/health | GET | Service health check | Phase 1 |
| /api/v1/chat | POST | Submit question, get cited answer | Phase 2 |

### 3.3 Project Structure

```
app/
├── main.py                     — FastAPI entry point, startup logic
├── core/
│   ├── config.py               — Environment settings (Pydantic)
│   └── database.py             — PostgreSQL async connection + pooling
├── models/
│   └── document.py             — Document tracking table (ORM)
└── services/
    ├── ingestion_service.py    — PDF → chunks → ChromaDB pipeline
    ├── rag_service.py          — Semantic search + LLM generation
    └── guardrails_service.py   — Emergency detection + PII removal
```

---

## 4. Development Progress

### Phase 1: Environment Setup and Data Ingestion ✅ COMPLETED

| Deliverable | Status |
|-------------|--------|
| FastAPI server with health check | Done |
| PostgreSQL database with connection pooling | Done |
| ChromaDB vector store configured | Done |
| PDF ingestion pipeline (parse → chunk → embed → store) | Done |
| 9 WHO guideline PDFs indexed (36,000+ chunks) | Done |
| Requirements and dependency management | Done |

### Phase 2: Core Logic and Agentic Workflow 🔧 IN PROGRESS

| Deliverable | Status |
|-------------|--------|
| RAG retrieval chain with relevance threshold | Done |
| Ollama LLM integration (local inference) | Done |
| Emergency query detection | Done |
| PII sanitization (email, phone, SSN, names) | Done |
| Citation enforcement in LLM prompt | Done |
| Chat API endpoint | Done |
| Verification layer (auto-retry on missing citations) | In Progress |
| LangGraph agent loop | Planned |
| Jargon simplifier | Planned |
| Simplification validation (cosine ≥ 0.85) | Planned |

---

## 5. Module Descriptions

### 5.1 config.py — Application Configuration

Centralizes all environment settings using Pydantic BaseSettings. Loads values from the `.env` file. Contains database URL, ChromaDB path, Ollama model name, and server settings. Makes the app portable across environments — just change the `.env` file.

### 5.2 database.py — PostgreSQL Connection

Sets up async SQLAlchemy with connection pooling. Pool size of 10 connections means 10 database connections stay open permanently and get reused across requests, avoiding the overhead of creating new connections. The `get_db()` function is a FastAPI dependency that provides each request its own session.

### 5.3 document.py — Document Tracking Model

Defines the `documents` table in PostgreSQL. Every PDF we ingest gets a record here — filename, file size, how many chunks were created, and processing status (pending → processing → completed). This lets us track what's been indexed in ChromaDB.

### 5.4 ingestion_service.py — PDF Processing Pipeline

The core of Phase 1. Takes a PDF file and:
1. Extracts text from each page using pdfplumber
2. Detects section headers (uppercase lines, numbered sections)
3. Splits text into ~1000 character chunks with 200 overlap for context continuity
4. Tags each chunk with metadata (source, page number, section header)
5. Embeds chunks using the BGE model and stores in ChromaDB

The section-aware chunking ensures retrieved context stays topically coherent instead of being cut at arbitrary character positions.

### 5.5 rag_service.py — RAG Pipeline (Phase 2)

The core AI engine:
1. Embeds the user's question using the same BGE model
2. Searches ChromaDB for the 3 most similar document chunks
3. Applies a relevance threshold (0.45) — rejects weak matches to prevent hallucination
4. Passes relevant chunks to Ollama LLM with a strict system prompt: "Answer ONLY from these documents, cite sources, refuse if information isn't there"
5. Returns the answer with source references

The relevance threshold is critical — if no documents are relevant enough, the system says "I cannot provide information" rather than generating unreliable content from the LLM's training data.

### 5.6 guardrails_service.py — Safety Layer (Phase 2)

Runs before any query reaches the LLM. Two functions:

**Emergency Detection:** Regex patterns match crisis language ("heart attack", "can't breathe", "kill myself", "overdose", "pain in chest"). When matched, returns emergency services numbers (112/108 India, 911 US) instead of trying to provide medical advice.

**PII Sanitization:** Detects email addresses, phone numbers (US and Indian 10-digit format), Social Security numbers, and names. Replaces them with [REDACTED] tags so personal data never reaches the LLM, is never stored in logs, and is never visible to administrators reviewing the system.

### 5.7 seed_documents.py — Data Loading Script

Run once during initial setup. Iterates through all PDF and text files in `sample_docs/`, processes each one through the ingestion pipeline, and reports how many chunks were stored. After running, ChromaDB contains 36,000+ searchable chunks from 9 WHO medical guidelines.

### 5.8 main.py — Application Entry Point

Creates the FastAPI server. On startup, initializes the database tables. Defines two endpoints:
- `GET /api/v1/health` — confirms the service is operational (Phase 1)
- `POST /api/v1/chat` — accepts a health question, runs it through guardrails and the RAG pipeline, returns a cited answer (Phase 2)

---

## 6. How to Run

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Ollama (https://ollama.ai)

### Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Pull the LLM model
ollama pull qwen2:1.5b

# Create PostgreSQL database
# Update .env with your credentials

# Load documents into ChromaDB
python seed_documents.py
```

### Running
```bash
# Terminal 1: Start Ollama
ollama serve

# Terminal 2: Start Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Testing
```bash
# Health check
curl http://localhost:8000/api/v1/health

# Ask a question
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are symptoms of diabetes?"}'
```

---

## 7. Next Steps

### Remaining Phase 2 Work
- Verification layer: auto-retry when LLM answer lacks citations
- LangGraph agent: multi-step classify → retrieve → generate → verify loop
- Jargon simplifier: rewrite clinical text in plain language
- Simplification validation: ensure rewrite preserves meaning (cosine ≥ 0.85)

### Phase 3 (Planned)
- React frontend with chat interface
- Source citation sidebar
- Toggle between clinical and plain-language answers
- Thumbs up/down feedback mechanism
- Emergency alert modal

### Phase 4 (Planned)
- End-to-end accuracy testing
- Document validation pipeline (admin approval before indexing)
- RLHF Golden Dataset export
- Security review and HIPAA-inspired compliance audit
- Final documentation

---

## Appendix: Source Documents

| # | Document | Topic | ISBN |
|---|----------|-------|------|
| 1 | 9789240033986-eng | Hypertension Treatment | 978-92-4-003398-6 |
| 2 | 9789240048126-eng | Tuberculosis Treatment | 978-92-4-004812-6 |
| 3 | 9789240081062-eng | Global Report on Hypertension | 978-92-4-008106-2 |
| 4 | 9789240084278-eng | Mental Health (mhGAP) | 978-92-4-008427-8 |
| 5 | 9789241504713-eng | Clinical Handbook for Dengue | 978-92-4-150471-3 |
| 6 | 9789241547178-eng | Cardiovascular Disease Prevention | 978-92-4-154717-8 |
| 7 | 9789241549912-eng | Antenatal Care | 978-92-4-154991-2 |
| 8 | WHO-UCN-NCD-20.1-eng | Type 2 Diabetes Management | WHO/UCN/NCD/20.1 |
| 9 | 9789241565257-eng | Global Report on Diabetes | 978-92-4-156525-7 |

All documents sourced directly from WHO IRIS (https://iris.who.int) and verified for authenticity.
