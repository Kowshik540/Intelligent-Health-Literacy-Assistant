# Project Walkthrough Guide (for the demo video)

This is a speaker's guide for explaining the Intelligent Health Literacy Assistant.
It covers what each module does, how a request flows end to end, a suggested demo
script, and likely questions with answers. Read it, then explain the system in your
own words on camera — the goal is that whoever presents can genuinely describe how
each part works.

---

## 1. One-line summary

A health chatbot that answers questions from verified WHO medical documents (RAG),
with a deterministic safety layer that intercepts emergencies, classifies vital
signs by fixed clinical rules, checks drug interactions, and verifies the answer
before it reaches the user.

**Stack:** FastAPI (backend) · React + Vite (frontend) · Ollama local LLM ·
ChromaDB (vector store) · PostgreSQL/SQLite (data) · LangChain.

---

## 2. High-level architecture (say this first in the video)

```
User (React UI / Streamlit)
        │  POST /api/v1/chat
        ▼
FastAPI route (chat.py)
        ▼
ChatService  ── the orchestrator ──
   1. Guardrails      (emergency + PII)          guardrails_service.py
   2. Triage          (red flags, acuity)        clinical_triage_service.py
   3. Biometrics      (BP/HR/SpO2/glucose)       biometric_service.py
   4. Clarification   (ask 1 question if needed) clarification_service.py
   5. RAG             (retrieve + generate)      rag_service.py  (+ ChromaDB, Ollama)
   6. Simplify        (plain language)           jargon_simplifier.py
   7. Verify          (no contradiction)         output_verification_service.py
   8. Drug check      (interactions)             drug_interaction_service.py
   9. Persist         (save messages)            PostgreSQL/SQLite
        ▼
Response: clinical answer + simplified answer + citations
```

**The key design idea to emphasize:** anything involving *math, thresholds, or
safety decisions* is done in **Python code** (deterministic, predictable), not by
the LLM. The LLM only does *language* — turning verified facts into a clear,
empathetic answer. This is what prevents dangerous mistakes like calling 110/60
"hypertension" or telling someone with an 8/10 headache to "drink water".

---

## 3. Module-by-module explanation

### Backend entry & config

- **`app/main.py`** — Creates the FastAPI app. On startup it creates database
  tables, seeds a default demo user, pre-loads the embedding model, and prints a
  banner showing which database and LLM are active. Registers all API routes and
  enables CORS so the frontend can call it.
- **`app/core/config.py`** — All settings (database URL, Ollama URL/model,
  embedding model, Chroma path) loaded from environment / `.env`. Defaults to
  SQLite + Ollama so it runs with zero setup. Also silences a noisy ChromaDB
  telemetry bug.
- **`app/core/database.py`** — Async SQLAlchemy engine + session. Rewrites the DB
  URL to the async driver (`asyncpg` for Postgres, `aiosqlite` for SQLite) and
  provides the `get_db()` dependency used by every route.

### API routes (`app/api/v1/routes/`)

- **`chat.py`** — `POST /chat/` (main endpoint), `GET /chat/conversations`,
  `GET /chat/conversations/{id}`. Passes the message to `ChatService` and returns
  the answer + citations. Strips internal markers and citation tags from the
  displayed text.
- **`documents.py`** — Upload a medical PDF (`/ingest`), admin approval
  (`/ingest/approve/{id}`), list documents, and serve the original file.
- **`feedback.py`** — Thumbs up/down on answers, plus a "golden dataset" of
  corrections for future fine-tuning (RLHF-style).
- **`safety.py`** — Runs just the guardrails on a piece of text (used by the PII
  demo in the UI).
- **`health.py`** — Simple health check for uptime monitoring.

### The orchestrator

- **`app/services/chat_service.py`** — The brain. `process_message()` runs the
  whole pipeline in order (guardrails → session memory → triage → biometrics →
  clarification → RAG → simplify → verify → drug check → persist). It also handles
  multi-turn memory: it re-reads earlier messages in the conversation so a symptom
  mentioned now is judged against vitals mentioned earlier.

### Deterministic safety services (pure Python, no LLM — highlight these)

- **`clinical_triage_service.py`** — Scans the text for red-flag symptoms (chest
  pain, stroke signs, "worst headache of my life", severe pain ≥7/10, headache +
  fever = possible meningitis, acute abdomen, breathing trouble, etc.) and assigns
  an acuity level: `CRITICAL / HIGH / MODERATE / LOW`. If CRITICAL, the pipeline
  **skips everything else and returns an emergency directive immediately** — no
  follow-up questions.
- **`biometric_service.py`** — Finds vital signs in the text (blood pressure,
  heart rate, SpO2, temperature, glucose) and classifies them with fixed clinical
  thresholds. Example: 110/60 → "Normal"; 190/125 → "Hypertensive Crisis". These
  classifications are handed to the LLM as facts it must not change.
- **`output_verification_service.py`** — After the LLM answers, this checks the
  text against the biometric facts and acuity. If the answer contradicts a number
  (calls a normal reading "high") or downplays a serious symptom, it blocks the
  answer and the pipeline regenerates or prepends a correction.
- **`drug_interaction_service.py`** — Detects medications by name/class and flags
  dangerous combinations (e.g. ibuprofen + lisinopril → kidney/BP risk; suggests
  acetaminophen instead). Uses conversation memory, so a drug mentioned earlier is
  checked against one asked about later.
- **`guardrails_service.py`** — First line of defense: detects life-threatening
  emergency phrases and redirects to helplines, and removes personal information
  (email, phone, SSN) before anything is processed.

### RAG and language services

- **`rag_service.py`** — The retrieval-augmented generation engine. Embeds the
  question, searches ChromaDB for the most relevant document chunks, filters out
  irrelevant/epidemiological chunks, builds a prompt that includes the
  deterministic facts, and asks the LLM to write a cited answer. Falls back to
  general medical knowledge (clearly, no fake citations) when no document matches.
- **`jargon_simplifier.py`** — Rewrites the clinical answer into plain English
  (e.g. "myocardial infarction" → "heart attack") while keeping the structure and
  citations.
- **`llm_factory.py`** — One place that builds the chat model, embeddings, and
  vector store. Chooses Ollama or OpenAI based on config and works across
  LangChain package versions.
- **`clarification_service.py`** — For non-emergency personal symptoms, decides
  whether to ask one focused follow-up question before answering.
- **`ingestion_service.py`** — Splits uploaded PDFs/text into chunks with metadata
  (source, page, section) and stores them in ChromaDB.
- **`document_validation_service.py`** — Validates uploads: PDF only, computes a
  SHA-256 hash, checks the source against a trusted-publisher list (WHO/CDC/etc.).
- **`graph_agent.py`** — An optional LangGraph pipeline (classify → generate →
  safety check). Not on the main path; built only if used.

### Data layer

- **`app/models/`** — SQLAlchemy tables: `User`, `Conversation`, `Message`,
  `Document`, `Feedback`.
- **`app/schemas/`** — Pydantic request/response validation models.
- **`seed_documents.py`** — Builds the knowledge base from `./data/*.txt` into
  ChromaDB. Run once after cloning.

### Frontend

- **`frontend/`** — React + TypeScript + Vite. `src/config.ts` centralizes the
  backend URL. Talks to `/chat/`, `/documents`, `/feedback`, `/safety`.
- **`streamlit_app.py`** — A lightweight alternative UI in one file.

---

## 4. A request's journey (good to narrate over a live demo)

Take the message **"I take lisinopril, can I take ibuprofen for a headache?"**:

1. **Guardrails** — no emergency phrase, no PII → continue.
2. **Session memory** — combines this with earlier messages in the conversation.
3. **Triage** — a plain headache is not a red flag → LOW acuity.
4. **Biometrics** — no vitals mentioned → nothing to classify.
5. **Drug check** — sees *lisinopril* (ACE inhibitor) + *ibuprofen* (NSAID) →
   flags the interaction and suggests acetaminophen.
6. **RAG + simplify** — generates the health answer.
7. **Verify** — no contradiction → approved.
8. The interaction warning is placed at the top; the answer is saved and returned.

Then contrast with **"I have crushing chest pain radiating to my left arm"**:

1. **Triage** immediately flags a cardiovascular red flag → CRITICAL.
2. The pipeline **stops** and returns the emergency directive (call 112/108/911,
   don't drive, sit upright) with **no follow-up questions**.

---

## 5. Suggested demo script (5–7 minutes)

1. **Intro (30s):** one-line summary + the "code does the math, LLM does the
   language" idea.
2. **Architecture slide (1m):** walk the diagram in section 2.
3. **Live demo (3m):** run the backend + frontend and show:
   - A normal question: *"What are the symptoms of diabetes?"* → note the
     citations from WHO documents.
   - A biometric: *"My blood pressure is 110/60"* → note it's correctly "normal".
   - An emergency: *"I have chest pain"* → note the instant emergency response.
   - A drug interaction: the lisinopril + ibuprofen example.
4. **Code tour (2m):** open `chat_service.py` and show the pipeline order, then
   open `clinical_triage_service.py` and `biometric_service.py` to show the rules
   are plain Python, not the model.
5. **Wrap (30s):** mention tests (`python tests/test_all.py`, 26 checks) and that
   it runs from a fresh clone with SQLite + Ollama.

---

## 6. How to run it (for the recording)

```bash
pip install -r requirements.txt
ollama pull qwen2:1.5b
python seed_documents.py
uvicorn app.main:app --host 0.0.0.0 --port 8000
# in another terminal:
cd frontend && npm install && npm run dev   # http://localhost:5173
```

Open http://localhost:5173 (UI) or http://localhost:8000/docs (API docs).

---

## 7. Likely questions from the mentor (and answers)

- **"Why not let the LLM classify blood pressure?"** Because a language model is
  not a reliable calculator — it can label 110/60 as hypertension. We do all
  numeric classification in code with fixed clinical thresholds.
- **"How do you stop it giving unsafe advice?"** Three layers: triage intercepts
  emergencies before any generation; the prompt forbids downplaying red flags; and
  the output verifier blocks answers that contradict the facts or downplay acuity.
- **"Where do the citations come from?"** Every document chunk stored in ChromaDB
  keeps its source file, page, and section. The answer cites those; irrelevant
  population statistics are filtered out.
- **"What if the document library doesn't cover the question?"** It falls back to
  general medical knowledge, clearly, without inventing a citation.
- **"How is conversation memory handled?"** Prior user messages in the same
  conversation are aggregated and re-evaluated each turn, so vitals/symptoms from
  earlier turns still count.
- **"What's tested?"** `tests/test_all.py` runs 26 checks across PII, emergency
  detection, document validation, retrieval, generation, the database, and the API.

---

## 8. A note on attribution

When you say "who did what", describe it honestly based on how your team actually
worked. If parts were built with AI assistance, it's fine and common to say the
team used AI tooling and then reviewed, tested, and integrated the code — what
matters to a mentor is that you understand and can explain it, which this guide is
meant to help with.
