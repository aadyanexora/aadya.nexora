# Aadya — Nexora AI

**Application name:** Aadya – Nexora AI  
**Company:** Aidni Global LLP  
**Architect / Designer / Developer:** Hardikkumar Gajjar  

Minimal investor-demo ready full-stack app: FastAPI backend + Next.js frontend with RAG (FAISS) and local embeddings + Groq chat.

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
- Set `GROQ_API_KEY`, `SECRET_KEY` and `DATABASE_URL` in `.env`.
- FAISS index persists to volume `faissdata` configured in `docker-compose.yml`.
- A default super‑admin account is created on startup if it doesn't exist:
  - **email:** hardik@aidniglobal.com
  - **password:** Gaatha@1805
  Change or remove these credentials for production!

## Features & API Endpoints

### Authentication
- `POST /api/auth/register` – create a user and return JWT.
- `POST /api/auth/login` – obtain JWT for existing user.
- `GET /api/auth/me` – protected route returns current user info.

JWT tokens use `SECRET_KEY` and are required on protected endpoints via `Authorization: Bearer <token>` header.

### Chat & RAG
- `POST /api/chat/stream` – protected endpoint accepting `message` and optional `conversation_id`.
  * Saves user message to PostgreSQL.
  * Performs retrieval-augmented generation by embedding query via the locally-loaded
    `SentenceTransformer` model (`all-MiniLM-L6-v2`, 384‑dim), searching the FAISS index,
    and streaming a response from the Groq API.
  * Assistant replies saved to DB as well.

> **Embedding dimension:** updated to 384 after switching from OpenAI.


### Admin
- `POST /api/admin/ingest` – ingest arbitrary text documents (admin only). Adds documents to `documents` table and indexes embeddings into FAISS.

### Database
- PostgreSQL with tables for `users`, `conversations`, `messages`, and `documents`.
- SQLAlchemy ORM with session management in `app/db`.

### Vector Store
- FAISS used locally to store and query embeddings.
- Embeddings generated locally using the `sentence-transformers/all-MiniLM-L6-v2` model.
- Index persisted to disk under configured `FAISS_DIR`.  If the database is cleared,
  stale index files are removed automatically on startup (see `app/main.py`).

### Frontend
- Next.js 14 App Router with pages for home, login/register, dashboard, and chat.
- Minimal responsive UI storing JWT in `localStorage` and streaming chat responses.

### Docker
- Compose file configures Postgres, backend, and frontend services with volumes.
- Environment variables injected via `.env`.

### Environment Variables
- `GROQ_API_KEY`, `DATABASE_URL`, `SECRET_KEY`, and optional `FAISS_DIR`.

**Deployment/CI notes:**
- Ensure `.env` values are provided in your deployment environment;
  the backend reads them via `python-dotenv` (through `settings`).
- Persistent storage for the FAISS directory is required so that the vector index
  survives restarts.

# aadya.nexora