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
