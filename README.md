# Aadya — Nexora AI

Minimal investor-demo ready full-stack app: FastAPI backend + Next.js frontend with RAG (FAISS) and OpenAI embeddings.

Quick start (local):

1. Copy example env and fill values:

```bash
cp .env.example .env
# edit .env
```

2. Start services with Docker Compose:

```bash
docker compose up --build
```

3. Frontend: http://localhost:3000
   Backend: http://localhost:8000

Notes:
- Set `OPENAI_API_KEY`, `SECRET_KEY` and `DATABASE_URL` in `.env`.
- FAISS index persists to volume `faissdata` configured in `docker-compose.yml`.
# aadya.nexora