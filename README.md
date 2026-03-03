# Aadya — Nexora AI

**Application name:** Aadya – Nexora AI  
**Company:** Aidni Global LLP  
**Architect / Designer / Developer:** Hardikkumar Gajjar  

Minimal investor-demo ready full-stack app: FastAPI backend + Next.js frontend with RAG (FAISS) and local embeddings + Groq chat.  (uses SQLite by default; no database server required)

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

> note: the compose configuration now uses SQLite and no longer requires a Postgres
> container. chat is available without authentication by default; login/register
> remain optional for tracking conversations, and admin ingest is not exposed in
> the frontend UI.

3. Frontend: http://localhost:3000
   Backend: http://localhost:8000

Notes:
- Set `GROQ_API_KEY`, `SECRET_KEY` and `DATABASE_URL` in `.env`.
- FAISS index persists to volume `faissdata` configured in `docker-compose.yml`.
- The backend will automatically seed an administrator user on startup if one
  does not already exist. By default the credentials are:
  - **email:** `admin@example.com`  (override via `ADMIN_EMAIL` env)
  - **password:** `admin123`  (override via `ADMIN_PASSWORD` env)
  You can also run the helper script manually from the repository root:

```bash
# developer host (requires dependencies installed; may need to override DATABASE_URL)
python backend/seed_admin.py            # creates/updates admin user
python backend/seed_admin.py --email foo --password bar   # custom creds
```

  or execute the packaged version inside the backend container:

```bash
docker exec aadyanexora-backend-1 python -m app.seed_admin
# pass flags the same way or via ADMIN_EMAIL/ADMIN_PASSWORD env vars
```

  Change or remove these credentials for production!

## Features & API Endpoints

### Authentication
- `POST /api/auth/register` – create a user and return JWT (optional).
- `POST /api/auth/login` – obtain JWT for existing user (optional).
- `GET /api/auth/me` – returns current user info when authenticated.

JWT tokens use `SECRET_KEY` and are accepted on endpoints that support them, but
chat endpoints no longer require authentication in order to function.

### Chat & RAG
- `POST /api/chat/stream` – protected endpoint accepting `message` and optional `conversation_id`.
  * Saves user message to PostgreSQL.
  * Performs retrieval-augmented generation by embedding query via the locally-loaded
    `SentenceTransformer` model (`all-MiniLM-L6-v2`, 384‑dim), searching the FAISS index,
    and streaming a response from the Groq API.
  * Assistant replies saved to DB as well.

> **Embedding dimension:** updated to 384 after switching from OpenAI.


### Admin
- `POST /api/admin/ingest` – ingest arbitrary text documents (admin only).
  This endpoint is **not linked from the frontend**, keeping the UI clean.

### Database
- SQLite by default (`aadya.db` file) with tables for `users`, `conversations`, `messages`, and `documents`.
- You can override `DATABASE_URL` to point at another database if desired.
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

---

© 2026 Aidni Global LLP. All rights reserved.
Application designed, architected and developed by Hardikkumar Gajjar.