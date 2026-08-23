# Review Call — Progress Update
**Date:** August 19, 2026
**Project:** Intelligent Health Literacy Assistant
**Team:** Bhavya, Manogna, Naga Laxmi, Kowshik, Dharani Thanuja

---

## Current Status

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | Environment setup and data ingestion | ✅ Completed |
| Phase 2 | Core logic and agentic workflow | 🔧 In Progress |
| Phase 3 | UI development and integration | Planned |
| Phase 4 | Testing, validation, documentation | Planned |

---

## Phase 1 — What Was Delivered (Weeks 1-3)

### 1. Development Environment
- Python 3.11 with FastAPI as the backend framework
- Virtual environment with all dependencies managed via `requirements.txt`
- Project structure following MVC pattern (models, services, routes)

### 2. PostgreSQL Database
- Async connection using SQLAlchemy with connection pooling (10 connections)
- Document tracking table created (filename, status, chunk count, timestamps)
- Connection pooling ensures efficient handling of concurrent requests

### 3. ChromaDB Vector Store
- Installed and configured for local persistence
- Using BGE (BAAI/bge-small-en-v1.5) embedding model
- Stores 384-dimensional vectors for semantic similarity search

### 4. PDF Ingestion Pipeline
- Extracts text from PDF pages using pdfplumber
- Section-aware chunking (~1000 characters, 200 overlap)
- Each chunk tagged with metadata: source filename, page number, section header
- Embeddings generated and stored in ChromaDB

### 5. Initial Document Set Indexed
- 9 verified WHO medical guideline PDFs ingested
- Topics: diabetes, hypertension, TB, mental health, cardiovascular disease, dengue, maternal health
- Total: 36,000+ searchable document chunks in ChromaDB

### 6. Health Check API
- `GET /api/v1/health` — confirms server is running
- Returns service name, version, and status

---

## Phase 2 — What's Done So Far (Weeks 4-6)

### 1. RAG Retrieval Chain (Working)
- User question is embedded using BGE model
- ChromaDB is searched for top 3 most similar document chunks
- Relevance threshold (0.45) filters out weak matches
- If nothing relevant found → system refuses to answer (prevents hallucination)

### 2. LLM Integration via Ollama (Working)
- Using qwen2:1.5b model running locally
- No data transmitted to any external service
- System prompt constrains LLM to only use provided document context
- Maximum 200 tokens per response to keep answers concise

### 3. Emergency Detection (Working)
- Pattern-based detection of crisis language
- Catches: heart attack, suicide, overdose, chest pain, can't breathe
- Returns emergency guidance (112/108 India) instead of medical advice
- Non-emergency health questions pass through normally

### 4. PII Sanitization (Working)
- Detects: email, phone numbers (US + Indian format), SSN, names
- Replaces with [REDACTED] tags before query reaches LLM
- Original PII never stored in database or logs
- User is notified when personal info is detected and removed

### 5. Citation Enforcement (Working)
- LLM prompt requires every answer to end with [Source: filename, Page: X]
- If LLM doesn't include citation, it's appended programmatically
- Citations reference the actual document chunks retrieved from ChromaDB

### 6. Chat Endpoint (Working)
- `POST /api/v1/chat` — accepts question, returns cited answer
- Full pipeline: guardrails → search → generate → respond

---

## Phase 2 — What's Still Pending

| Feature | Description | Status |
|---------|-------------|--------|
| Verification Layer | Auto-retry when LLM doesn't cite sources | Started |
| LangGraph Agent | Multi-step: classify → retrieve → generate → verify | Planned |
| Jargon Simplifier | Rewrite clinical language to plain English | Planned |
| Simplification Validation | Cosine similarity ≥ 0.85 check | Planned |

---

## GitHub Repository

**URL:** https://github.com/Kowshik540/Intelligent-Health-Literacy-Assistant

### Files in Repository
```
├── README.md                    — Project progress overview
├── requirements.txt             — Python dependencies
├── .env.example                 — Environment configuration template
├── seed_documents.py            — Script to load WHO PDFs into ChromaDB
└── app/
    ├── main.py                  — FastAPI server (health check + chat endpoint)
    ├── core/
    │   ├── config.py            — Environment settings (DB, ChromaDB, Ollama)
    │   └── database.py          — PostgreSQL async connection with pooling
    ├── models/
    │   └── document.py          — Document tracking table schema
    └── services/
        ├── ingestion_service.py — PDF parsing → chunking → ChromaDB (Phase 1)
        ├── rag_service.py       — RAG pipeline: search + LLM generation (Phase 2)
        └── guardrails_service.py — Emergency detection + PII removal (Phase 2)
```

---

## Demo (If Asked)

### Show RAG Working:
```
Question: "What are symptoms of diabetes?"
Answer: "Symptoms include thirst, frequent urination, blurred vision, fatigue..."
Source: WHO-UCN-NCD-20.1-eng.pdf, Page 12
```

### Show Emergency Detection:
```
Question: "I am having pain in my chest"
Response: "EMERGENCY DETECTED — Contact 112 (India) or 108 (Ambulance)"
```

### Show PII Sanitization:
```
Input: "my email is test@gmail.com what is fever"
Processed as: "[EMAIL_REDACTED] what is fever"
```

### Show Refusal (No Hallucination):
```
Question: "How to cook biryani"
Response: "I cannot provide information on this topic. Please consult a healthcare professional."
```

---

## Next Steps (Phase 2 Remaining)

1. Complete the verification layer (auto-retry on missing citations)
2. Implement LangGraph agent loop for multi-step reasoning
3. Build the jargon simplifier (clinical → plain language)
4. Add simplification validation (cosine similarity check)

---

## Questions for Reviewer

- Any feedback on the RAG pipeline approach?
- Should we prioritize the jargon simplifier or the verification layer next?
- Any concerns about the document validation workflow planned for Phase 3?
