# Backend Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies needed by some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (better layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and data
COPY app/ ./app/
COPY data/ ./data/
COPY seed_documents.py .

# Expose the API port
EXPOSE 8000

# Seed the knowledge base, then start the server.
# Seeding is idempotent — it skips documents already indexed in ChromaDB.
CMD ["sh", "-c", "python seed_documents.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
