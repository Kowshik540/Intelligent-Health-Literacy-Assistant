# PROJECT DOCUMENTATION

## Intelligent Health Literacy Assistant

A RAG-based application that answers health questions only from verified medical documents

**Project 1 — Healthcare Domain**

**Status:** Working End-to-End Prototype — Phase 3 Complete, Phase 4 In Progress

**Team Members**
- Bhavya Konagala
- Bachina Manogna
- A Naga Laxmi
- Kowshik Thota
- K. Dharani Thanuja

**Document Version:** 3.0
**Last Updated:** September 2, 2026

---

## Table of Contents

1. Executive Summary & Objectives
2. System Architecture
3. Functional Requirements
4. Technical Specifications
5. AI & Agentic Framework Logic
6. Security & Compliance
7. Success Metrics (KPIs)
8. Project Roadmap

Appendix A: Development Progress by Module
Appendix B: Source Verification Log
Appendix C: Demonstration Walkthrough

---

## 1. Executive Summary & Objectives

### 1.1 Problem Statement

People often search online for health information, but results are frequently confusing, contradictory, or unreliable. Medical jargon is difficult to understand, and there is no clear way to verify the source or accuracy of the information. This can lead to risky health decisions.

We have built a RAG-based application that provides clear, evidence-based medical answers only from verified sources such as WHO guidelines, government protocols, and certified journals. Every response includes citations, and the system refrains from answering when information is unavailable.

### 1.2 Project Scope

**In-Scope**

- A RAG-based application that ingests medical PDFs (guidelines, journal excerpts, institutional protocols) and answers questions using only that content.
- A citation system that shows the source PDF and page number behind every answer.
- An explicit "I don't know" response when the retrieved content doesn't actually answer the question.
- A simplification step that rewrites clinical answers into plain, everyday language.
- Handling for emergency-sounding queries, so the application doesn't try to give medical advice in situations where it shouldn't.
- A document validation pipeline that verifies the trustworthiness of uploaded PDFs before they enter the vector store.
- PII transparency measures so users can trust their personal data is never stored.
- A simplification validation step that confirms the plain-language rewrite has not introduced hallucinated content.

**Out-of-Scope**

- No integration with hospital systems or electronic health records.
- No diagnosis, prescriptions, or treatment recommendations — the application explains information, it doesn't practice medicine.

### 1.3 Strategic Objective

The primary value proposition is patient safety through verifiability: every answer the system produces must be defensible against its source document. By pairing a citation-enforcing RAG pipeline with safety guardrails and a jargon simplifier, the application raises health literacy without ever substituting for professional medical judgment.

### 1.4 Progress Since Last Review

At the previous review, the frontend, backend, and ChromaDB modules existed independently. Since then, the modules have been fully integrated into a single working application:

- The React frontend now talks to the live FastAPI backend (no more mock data).
- The full RAG pipeline is operational: retrieval, citation, refusal, simplification, and validation all run end-to-end against real WHO documents.
- PostgreSQL persists every conversation, message, document, and feedback record.
- Safety guardrails (emergency detection, PII redaction) run on every query.
- A local LLM (via Ollama) generates answers with no data leaving the machine.
- An automated test suite of 26 checks passes at 100%.

---

## 2. System Architecture

### 2.1 High-Level Architecture

The system has three main parts: a frontend where users chat with the assistant, a backend that handles the logic of retrieving and generating answers, and a data layer that stores the processed medical documents and interaction history.

*(Figure 1: High-Level System Architecture)*

### 2.2 Data Ingestion Pipeline

Raw medical PDFs (clinical guidelines, journal excerpts, institutional protocols) are processed through the following stages:

1. **Parsing:** Text is extracted from the PDF while preserving document structure — headings, tables, and page boundaries.
2. **Cleaning:** Extracted text is normalized (whitespace, encoding, boilerplate removal).
3. **Chunking:** Content is split into semantically coherent chunks aligned to section boundaries rather than fixed character counts.
4. **Metadata Tagging:** Each chunk is tagged with source PDF title, page number, and section header, forming the basis of the citation engine.
5. **Embedding:** Chunks are embedded using the BGE embedding model, chosen for its accuracy on domain-dense medical text.
6. **Vectorization & Storage:** Embeddings and metadata are persisted in ChromaDB for local semantic retrieval.

*(Figure 2: Data Ingestion Pipeline)*

### 2.3 Component Interaction

A user request travels through the system as follows:

1. The user submits a question through the React (Vite) chat interface.
2. The FastAPI backend receives the request and coordinates the rest of the pipeline.
3. Greeting/small-talk detection intercepts non-medical messages (for example "hello") and responds without retrieval, so greetings never produce a false citation.
4. PII sanitization scans the query and redacts any personal identifiers before further processing.
5. Emergency detection checks for crisis-related language — if matched, the system returns emergency guidance (India 112/108 and international helplines) and stops processing.
6. The request is forwarded to the RAG orchestration layer, which manages the retrieval-and-generation flow.
7. The orchestration layer queries ChromaDB for the most relevant chunks via semantic similarity search.
8. If no chunks pass the relevance threshold, the system refuses to answer rather than guessing, and attaches no citations.
9. Retrieved chunks, with their metadata, are passed to the LLM with a system prompt constraining it to answer only from the provided context and to cite sources.
10. The generated answer is checked to confirm every claim has a citation; refusals produced by the model itself are stripped of misleading citations.
11. The verified answer is routed through the Jargon Simplifier to produce a plain-language version.
12. The simplified version passes through Simplification Validation (cosine similarity + citation preservation) to confirm it hasn't hallucinated or altered meaning.
13. The response and its citations are returned to the frontend, which renders the answer alongside a source panel highlighting the exact PDF snippet used.
14. PostgreSQL logs the interaction and any user feedback.

*(Figure 3: Component Interaction — Request Flow)*

---

## 3. Functional Requirements

### 3.1 User Stories

| User Role | Action (I want to...) | Benefit (So that...) |
|-----------|----------------------|---------------------|
| Patient | ask a health question in plain language | I can understand my condition without needing to interpret clinical jargon myself |
| Patient | see the exact source and page number behind an answer | I can verify the information myself before trusting it |
| Patient | be redirected to emergency guidance for urgent symptoms | I do not rely on a chatbot during a medical emergency |
| Patient | toggle between clinical and plain-language explanations | I can choose the level of detail that suits my understanding |
| Patient | use a light or dark theme | I can read comfortably in different lighting conditions |
| Patient | ask questions by voice | I can interact hands-free |
| Patient | know that my personal information is not stored anywhere | I can trust the system with sensitive health questions |
| Administrator | validate uploaded documents before they enter the knowledge base | only trusted, verified sources are used for answering |
| Administrator | review logged feedback and citation corrections | I can curate a dataset for future fine-tuning |
| Administrator | confirm that access to ingestion endpoints is restricted | only authorized team members can add source material |

### 3.2 Acceptance Criteria

| Feature | Acceptance Criteria | Status |
|---------|-------------------|--------|
| Citation Engine | Every generated answer includes at least one citation (PDF title + page number). | Met |
| Source Panel | The exact retrieved snippet is shown in the source panel and matches the text used to generate the answer. | Met |
| Refusal on Missing Data | If retrieved context does not contain the answer, the system responds with an explicit inability-to-answer message and no citation, rather than a generated guess. | Met |
| Emergency Handling | High-risk queries are detected and answered with emergency guidance instead of clinical content. | Met |
| Greeting Handling | Greetings and small-talk are answered conversationally with no retrieval and no citation. | Met |
| Jargon Simplifier | The plain-language rewrite preserves factual meaning while reducing reading complexity. | Met |
| Document Validation | Uploaded PDFs pass file-type check, metadata verification, and admin approval before entering ChromaDB. Pending documents are never searchable. | Met |
| PII Transparency | Personal information is detected and removed. Raw PII is never stored — only redacted versions appear in logs. | Met |
| Simplification Validation | The simplified answer passes semantic similarity check (≥ 0.85 against original) and citation preservation before being returned. | Met |

---

## 4. Technical Specifications

### 4.1 Technology Stack

| Component | Technology | What It's For |
|-----------|-----------|--------------|
| Frontend | React (Vite) + TypeScript | The chat interface, knowledge browser, safety showcase, and source verification panel. |
| Backend | FastAPI (async) | Handles incoming requests and coordinates the pipeline. |
| AI Workflow | LangChain | Manages the retrieval-and-generation logic. |
| Vector Database | ChromaDB | Stores and searches document embeddings locally. |
| PDF Processing | pdfplumber | Reads and parses medical PDFs, preserving structure for citations. |
| Embeddings | BGE (HuggingFace) | Converts text into vectors for semantic search. |
| Answer Generation | qwen2:1.5b (via Ollama) | Generates answers strictly from retrieved content. Runs locally — no data leaves the server. |
| Database | PostgreSQL (async SQLAlchemy) | Stores conversations, messages, documents, and feedback. |
| Migrations | Alembic | Versioned database schema migrations. |
| Observability | LangSmith (optional) | Tracing the AI workflow when enabled. |

### 4.2 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/chat/ | POST | Accepts a user query; returns clinical + simplified answer with citations. |
| /api/v1/chat/conversations | GET | Lists saved conversations for history. |
| /api/v1/chat/conversations/{id} | GET | Retrieves a conversation with all messages. |
| /api/v1/ingest | POST | Uploads and validates a new PDF guideline. |
| /api/v1/ingest/approve/{id} | POST | Admin approves a validated document for ChromaDB indexing. |
| /api/v1/documents | GET | Lists documents with status, trust, and chunk count. |
| /api/v1/sources/{doc_id} | GET | Retrieves metadata for a specific cited source. |
| /api/v1/feedback/ | POST | Submits thumbs-up/down and optional correction for a response. |
| /api/v1/safety/check | POST | Runs text through the guardrails layer (PII + emergency) without calling the LLM. |
| /api/v1/health | GET | Service health check for uptime monitoring. |

### 4.3 Deployment Environment

- Local development with three processes: Ollama (LLM), FastAPI backend on port 8000, React frontend on port 5173.
- Docker Compose configuration provided for teammates (Postgres + backend + frontend).
- Environment-based secrets management for database credentials.
- LLM runs locally via Ollama — no external API dependencies, no data transmitted to third parties.

---

## 5. AI & Agentic Framework Logic

### 5.1 System Prompt Strategy

The system prompt constrains the LLM to a closed-book, citation-first behavior: it answers strictly using the retrieved context chunks provided to it, attaches a document/page citation to every factual claim, and explicitly declines to answer when the retrieved context does not contain sufficient information. It is also instructed to refuse when the retrieved text is only an index, table of contents, or page reference.

### 5.2 RAG Implementation

- **Retrieval Strategy:** Semantic search over ChromaDB using BGE embeddings.
- **Chunking Strategy:** Section-aware chunking, so retrieved context stays topically coherent.
- **Context Assembly:** Each chunk is passed to the LLM alongside its source metadata, so citations are generated deterministically.
- **Relevance Threshold:** Only chunks scoring at or above the relevance threshold are used for generation. Below this, the system refuses to answer.
- **Greeting Bypass:** Greetings and small-talk are detected up front and answered without retrieval, avoiding false citations on non-medical input.

### 5.3 Document Validation (Before ChromaDB)

When an administrator uploads a PDF, it does not enter ChromaDB immediately. It passes through a validation pipeline to ensure only trusted documents become part of the knowledge base:

| Validation Step | What It Checks | Fail Action |
|----------------|---------------|-------------|
| File type check | Only PDF format accepted | Reject upload |
| Metadata extraction | Look for publisher name, ISBN, reference number | Flag if missing |
| Source whitelist | Check if publisher matches trusted sources (WHO, CDC, NIH, ICMR, certified journals) | Flag if unknown source |
| Hash generation | SHA-256 hash of the file for tamper detection | Store hash for future comparison |
| Admin approval | Human administrator reviews and explicitly approves | Document stays in "pending" until approved |

Only documents marked as verified and approved by an administrator proceed to the chunking → embedding → ChromaDB pipeline. Pending or rejected documents are never indexed and never appear in search results.

### 5.4 Verification Layer

Before an answer is returned to the user, a validation step confirms that the generated response is backed by a citation pointing to an actual retrieved chunk. When the model itself declines to answer, any citation is stripped so refusals are never presented as verified responses.

### 5.5 Guardrails & Hallucination Control

- **Closed-book prompting:** the model is restricted to retrieved context only, with no reliance on general knowledge for clinical claims.
- **Explicit refusal path:** absence of sufficient context produces a stated inability to answer, with no citation, instead of a best-effort guess.
- **Emergency query detection:** pattern-based detection of emergency language (heart attack, chest pain, overdose, self-harm, difficulty breathing) redirects users to emergency guidance instead of generating clinical advice.
- **Greeting detection:** conversational messages are separated from medical queries to keep the citation trail honest.

### 5.6 Medical Jargon Simplifier

Once a cited clinical answer is generated, an auxiliary step rewrites it into plain, everyday language — for example, explaining that Myocardial Infarction is a Heart Attack — while preserving the original citations, so the simplified version remains just as traceable as the clinical one. The frontend lets the user toggle between the Clinical and Plain Language versions.

### 5.7 Simplification Validation

To ensure the rewrite has not introduced hallucinated content or altered the factual meaning, a validation step runs before the simplified answer is returned:

| Validation Check | How It Works | Fail Action |
|-----------------|-------------|-------------|
| Citation preservation | Verify that citations from the original clinical answer are carried into the simplified version | Retry simplification |
| Semantic similarity | Compare the embedding of the original answer with the simplified version — similarity must be ≥ 0.85 (cosine) | Retry simplification |
| Fallback | If repeated attempts fail, keep the best available plain-language text and re-attach original citations | Return validated result |

---

## 6. Security & Compliance

### 6.1 PII Handling

User input is checked for personally identifiable information before being forwarded to the LLM or persisted in any log. Detected identifiers are redacted prior to storage, in line with HIPAA-inspired handling of protected health information. The phone-number detector covers international formats and Indian 10-digit mobile numbers.

### 6.2 PII Transparency — How Users Can Trust Their Data Is Not Stored

- **Redaction before processing:** PII (email, phone, SSN, DOB, medical record numbers, address, name) is detected and replaced with `[REDACTED]` tags before the query reaches the LLM.
- **Sanitized query only:** The database stores only the sanitized version of the query.
- **Local LLM (via Ollama):** Because the LLM runs on the same server, user queries are never transmitted to any external API or third-party service.
- **User notification:** The frontend indicates when personal information is detected and removed.
- **Audit verification:** An administrator reviewing the logs only sees redacted entries.

### 6.3 Access Control

- Document ingestion is separated into upload → validation → explicit admin approval; upload alone does not index a document.
- Only trusted, approved, and completed documents are exposed to users in the Knowledge view.

### 6.4 Audit Logging

Every interaction — the query (sanitized), the retrieved sources, the generated answer, and any user feedback — is logged to PostgreSQL with a timestamp, creating an auditable trail of what the system answered and from which document.

### 6.5 HIPAA-Inspired Practices

While the system does not process actual patient health records, it follows HIPAA-inspired principles: data minimization, PII redaction, access logging, local processing (no external data transmission), and a clear disclaimer that the tool is for health literacy and education, not diagnosis or treatment.

---

## 7. Success Metrics (KPIs)

| Metric | Definition / Target | Current Result |
|--------|-------------------|----------------|
| Automated Test Coverage | Full-system test suite covering PII, emergency, validation, RAG, DB, and endpoints | 26 / 26 passing (100%) |
| Retrieval Relevance | Cosine similarity of top retrieved chunk to the query on core topics | Diabetes 0.76, Hypertension 0.70, Fever 0.65 |
| Latency | Time from query submission to answer with citation | ~8 seconds (local LLM) |
| Hallucination Control | Answers refuse when no relevant verified document exists; no citation on refusal | Enforced |
| Emergency Detection | Correctly blocks heart attack, chest pain, overdose, self-harm, breathing difficulty | Verified |
| PII Compliance | No raw PII stored; email, phone (incl. Indian mobile), SSN, name redacted | Verified |
| Document Trust Filter | WHO / CDC / ICMR accepted; untrusted sources flagged | Verified |
| Persistence | Conversations, messages, documents, and feedback stored in PostgreSQL | Verified (5 tables active) |

---

## 8. Project Roadmap (8 Weeks)

| Phase | Weeks | Focus | Key Deliverables | Status |
|-------|-------|-------|-----------------|--------|
| Phase 1 | Weeks 1–2 | Environment setup and data collection | Dev environment, dependency setup, verified WHO PDFs, PostgreSQL schema, React project init, ChromaDB installation | Complete |
| Phase 2 | Weeks 3–4 | Data pipeline and document validation | PDF parsing, section-aware chunking, metadata tagging, document validation pipeline, BGE embedding, ChromaDB storage | Complete |
| Phase 3 | Weeks 5–6 | Core AI logic and safety features | RAG retrieval chain, citation enforcement, verification layer, refusal logic, emergency detection, greeting handling, jargon simplifier, simplification validation, PII redaction, frontend-backend integration | Complete |
| Phase 4 | Weeks 7–8 | Integration, testing, and final delivery | End-to-end integration, feedback system, accuracy/hallucination testing, security review, frontend polish, final documentation | In Progress |

**Review cadence:** Progress review meeting every 2 weeks (end of each phase).

---

## Appendix A: Development Progress by Module

The project is divided into five functional modules, each owned by a team member and tracked independently. This section reflects real, ground-level progress.

### A.1 Documentation & Project Planning — Owner: K. Dharani Thanuja

**Status:** Ongoing — updated each review

**Work Completed**
- Maintained project documentation covering problem statement, objectives, scope, architecture, workflow, and tech stack.
- Sourced and verified WHO guideline PDFs across multiple clinical areas.
- Verified each source against official WHO and government repositories before ingestion.

### A.2 PDF Processing & ChromaDB — Owner: Bachina Manogna

**Status:** Complete and integrated with the RAG pipeline

**Work Completed**
- Installed and configured ChromaDB with a persistent local collection.
- Stored document embeddings with page-level and section-level metadata.
- Implemented similarity search with relevance scoring.
- Integrated ChromaDB with the FastAPI backend and RAG retrieval pipeline.
- Verified storage and retrieval end-to-end.

### A.3 Backend & AI Pipeline — Owner: Kowshik Thota

**Status:** Complete — full pipeline operational

**Work Completed**
- Built the FastAPI backend with a clean layered structure (routes, services, repositories, models).
- Implemented the RAG service with citation enforcement and refusal logic.
- Implemented PII sanitization and emergency detection guardrails.
- Implemented the jargon simplifier and simplification validation (cosine similarity + citation preservation).
- Added greeting handling so non-medical messages don't produce false citations.
- Connected PostgreSQL with async SQLAlchemy and Alembic migrations.
- Exposed a safety-check endpoint for testing guardrails independently of the LLM.

### A.4 Frontend (React/Vite) — Owner: Bhavya Konagala

**Status:** Complete — integrated with the live backend

**What Was Built**
- A multi-page interface: Overview, Assistant, Knowledge, and Safety.
- The Assistant page connects to the live backend, with Clinical / Plain-Language toggle, citations, conversation history, voice input, and feedback.
- The Knowledge page lists only verified, approved, indexed documents from the backend.
- The Safety page demonstrates the guardrails, including a live PII check.
- Added a working light/dark theme toggle with the preference saved between sessions.

### A.5 Database, Testing & Integration — Owner: A Naga Laxmi

**Status:** Complete — integration and test suite in place

**Work Completed**
- PostgreSQL schema for users, conversations, messages, documents, and feedback.
- Full-system automated test suite (26 checks) covering guardrails, validation, retrieval, generation, database, and endpoints.
- End-to-end integration verification of all modules together.

---

## Appendix B: Source Verification Log

Before ingestion, every source PDF collected for the knowledge base was checked for authenticity. Each file was inspected for embedded metadata (producer, creator, and revision dates), cross-checked for its ISBN or official WHO document reference number, and confirmed to contain WHO's standard cataloguing text.

| # | Document | Topic | ISBN / Reference No. | WHO Branding | Verdict |
|---|----------|-------|---------------------|-------------|---------|
| 1 | 9789240033986-eng | Hypertension — Pharmacological Treatment Guideline | 978-92-4-003398-6 | Confirmed | Genuine |
| 2 | 9789240048126-eng | Tuberculosis — Treatment (Module 4) | 978-92-4-004812-6 | Confirmed | Genuine |
| 3 | 9789240081062-eng | Global Report on Hypertension | 978-92-4-008106-2 | Confirmed | Genuine |
| 4 | 9789240084278-eng | mhGAP — Mental Health Guideline | 978-92-4-008427-8 | Confirmed | Genuine |
| 5 | 9789241504713_eng | Clinical Handbook for Dengue | 978-92-4-150471-3 | Confirmed | Genuine |
| 6 | 9789241547178_eng | Prevention of Cardiovascular Disease | 978-92-4-154717-8 | Confirmed | Genuine |
| 7 | 9789241549912-eng | Antenatal Care Recommendations | 978-92-4-154991-2 | Confirmed | Genuine |
| 8 | WHO-UCN-NCD-20.1-eng | Diagnosis & Management of Type 2 Diabetes | WHO/UCN/NCD/20.1 (doc ref) | Confirmed | Genuine |
| 9 | 9789241565257_eng | Global Report on Diabetes | 978-92-4-156525-7 | Confirmed | Genuine |

All documents passed verification: filename ISBNs matched the ISBNs embedded within the document text, WHO's standard cataloguing/copyright notice was present in each file, and metadata was consistent with WHO's official publishing workflow.

---

## Appendix C: Demonstration Walkthrough

This walkthrough mirrors what is shown live during the review.

1. **Start the system.** Three processes run locally: the Ollama LLM, the FastAPI backend on port 8000, and the React frontend on port 5173. The app opens at http://localhost:5173.

2. **Overview page.** Introduces the platform and its purpose.

3. **Assistant page — a valid medical question.** Asking "what should I take for a fever" returns a cited answer drawn from the verified guidelines, with a Clinical / Plain-Language toggle and a source panel showing the exact snippet and page.

4. **Assistant page — a greeting.** Typing "hello" returns a friendly conversational reply with no citation and no verified badge, showing that non-medical input is handled honestly.

5. **Assistant page — an out-of-scope question.** A question with no supporting document returns an explicit refusal with no citation, demonstrating hallucination control.

6. **Emergency handling.** A message such as "I am having chest pain" returns emergency guidance with India (112 / 108) and international helpline numbers instead of clinical content.

7. **Safety page.** The live PII check redacts an email or phone number in real time, and the guardrail modules are listed.

8. **Knowledge page.** Lists only trusted, approved, indexed documents with their chunk counts.

9. **Theme toggle.** The light/dark switch in the header changes the whole interface and remembers the choice.

10. **Persistence.** Conversation history is available in the Assistant, and every interaction is stored in PostgreSQL.
