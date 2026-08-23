# Setup Guide for Teammates

## Option 1: Docker (Recommended — No Installation Required)

Just install Docker Desktop and run one command:

```bash
# Clone the repo
git clone https://github.com/Kowshik540/Intelligent-Health-Literacy-Assistant.git
cd Intelligent-Health-Literacy-Assistant

# Start everything (PostgreSQL + Backend + Frontend)
docker-compose up

# Open in browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

That's it. Docker handles Python, Node, PostgreSQL — everything runs in containers.

To stop: `docker-compose down`

---

## Option 2: Manual Setup (If you want to run without Docker)

### Prerequisites
- Python 3.11+
- Node.js 18+
- PostgreSQL 14+
- Ollama (https://ollama.ai)

### Steps

```bash
# 1. Clone
git clone https://github.com/Kowshik540/Intelligent-Health-Literacy-Assistant.git
cd Intelligent-Health-Literacy-Assistant

# 2. Backend setup
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 3. Create .env file (copy from .env.example and fill in your PostgreSQL credentials)
copy .env.example .env

# 4. Pull the LLM model
ollama pull qwen2:1.5b

# 5. Load documents into ChromaDB
python seed_documents.py

# 6. Start Ollama (Terminal 1)
ollama serve

# 7. Start Backend (Terminal 2)
uvicorn app.main:app --port 8003

# 8. Start Frontend (Terminal 3)
cd frontend
npm install
npm run dev

# 9. Open http://localhost:5173
```

---

## Running Tests

```bash
python tests/test_all.py
```

All 26 tests should pass.
