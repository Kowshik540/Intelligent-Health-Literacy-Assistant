# Setup Guide

This project runs on any machine with minimal setup. It uses a **local LLM (Ollama)** and a **local SQLite database by default**, so there is nothing to configure to get started.

There are two ways to run it.

---

## Option 1: Manual Setup (recommended for testing)

### Prerequisites
- Python 3.11+
- Node.js 18+
- [Ollama](https://ollama.com) (free local LLM runtime)

No database server is required — it uses a local SQLite file automatically.

### Steps

```bash
# 1. Clone
git clone https://github.com/Kowshik540/Intelligent-Health-Literacy-Assistant.git
cd Intelligent-Health-Literacy-Assistant

# 2. Backend: create a virtual environment and install dependencies
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS / Linux
pip install -r requirements.txt

# 3. Pull the local LLM model (one-time)
ollama pull qwen2:1.5b

# 4. Build the knowledge base (indexes ./data into ChromaDB)
python seed_documents.py

# 5. Start Ollama (Terminal 1)
ollama serve

# 6. Start the backend (Terminal 2)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# 7. Start the frontend (Terminal 3)
cd frontend
npm install
npm run dev

# 8. Open the app
#    Frontend:  http://localhost:5173
#    API docs:  http://localhost:8000/docs
```

That's it. No `.env` file is needed — SQLite and Ollama are the defaults.

### Optional configuration
Only if you want to change defaults, copy `.env.example` to `.env` and edit it:
- Use PostgreSQL instead of SQLite (set `DATABASE_URL`).
- Use OpenAI instead of Ollama (set `USE_OLLAMA=False` and `OPENAI_API_KEY`).
- Point the frontend at a different backend (create `frontend/.env` with `VITE_API_BASE_URL`).

---

## Using PostgreSQL instead of SQLite

The app works with SQLite out of the box, but if you want to run it against a
local PostgreSQL server (recommended for a production-like test):

1. Create the database and note your credentials:

   ```sql
   -- in psql, as the postgres superuser
   CREATE DATABASE healthcare_db;
   ```

2. Copy `.env.example` to `.env` and set `DATABASE_URL`. Use the async-friendly
   `postgresql://` scheme (the app converts it to `asyncpg` automatically):

   ```env
   DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/healthcare_db
   ```

   If your password contains special characters, URL-encode them
   (for example `#` becomes `%23`, `@` becomes `%40`).

3. Tables are created automatically on startup — no manual migration step is
   needed. (Alembic migrations are available in `alembic/` if you prefer to run
   them explicitly against PostgreSQL.)

The startup banner prints which database and LLM are active, so you can confirm
your configuration at a glance.

---

## Option 2: Docker

Install Docker Desktop, make sure Ollama is running on the host with the model pulled, then:

```bash
ollama pull qwen2:1.5b
docker-compose up --build
# Frontend:  http://localhost:3000
# API:       http://localhost:8000/docs
```

To stop: `docker-compose down`

---

## Running the Tests

```bash
venv\Scripts\activate
python tests/test_all.py
```

All 26 checks should pass (guardrails, PII, emergency detection, document validation,
RAG retrieval, LLM generation, database, and API endpoints).

---

## Scenarios you can try

Once the backend is running (and Ollama is up with the model pulled), you can
exercise every feature from the UI at `http://localhost:5173`, from the
interactive API docs at `http://localhost:8000/docs`, or with the Streamlit UI
(`streamlit run streamlit_app.py`). Things that work end to end:

| Scenario | What to type | Expected behaviour |
|----------|--------------|--------------------|
| Document-backed answer | "What are the symptoms of diabetes?" | Plain-language answer plus a clinical version, with citations (source PDF, page, section) shown in the sidebar. |
| General health question | "How can I improve my sleep?" | Helpful general answer, clearly labelled as general information (no citation), ending with a "confirm with a professional" note. |
| Emergency detection | "I am having a heart attack" | Immediate safety response with emergency helplines (112 / 108 for India). No document lookup. |
| PII redaction | "my email is john@gmail.com, what is hypertension?" | The email is stripped before processing; the answer still addresses hypertension. |
| Greeting / small talk | "hello" | A short friendly reply, no document retrieval. |
| Non-health / gibberish | "asdfghjkl" | Politely asks you to rephrase as a health question — it does not make anything up. |
| Follow-up questions | Describe a personal symptom | The assistant asks a clarifying question before answering. |
| Document upload | Upload a WHO PDF from `sample_docs/` via `POST /ingest`, then approve it via `POST /ingest/approve/{id}` | The PDF is validated, indexed into ChromaDB, and becomes searchable. |
| Feedback | Thumbs up / down on an answer | Recorded in the database; corrections build the "golden dataset" (`GET /feedback/golden-dataset`). |

---

## Troubleshooting

- **"Connection refused" in the UI** — the backend isn't running, or it's on a
  different port. Start it on port 8000, or set `VITE_API_BASE_URL` in
  `frontend/.env` to match.
- **Answers say "having trouble generating a response"** — Ollama isn't running
  or the model isn't pulled. Run `ollama serve` and `ollama pull qwen2:1.5b`.
- **No sources / empty Knowledge page** — run `python seed_documents.py` to build
  the vector store.
- **First request is slow** — the embedding model loads on startup (~30–60s).
  Wait for the startup banner before testing.
