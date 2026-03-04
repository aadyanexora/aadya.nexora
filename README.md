# Aadya — Nexora AI

**Application name:** Aadya – Nexora AI  
**Company:** Aidni Global LLP  
**Architect / Designer / Developer:** Hardikkumar Gajjar  

Minimal investor-demo ready full-stack app: FastAPI backend + Next.js frontend with RAG (FAISS) and local embeddings + Groq chat.  (requires PostgreSQL; no built-in SQLite fallback is provided)

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

> note: for production deployments the backend requires a PostgreSQL server.
> the compose configuration includes a `postgres` service that starts on
> `postgres:5432` and the default credentials are shown in the `.env.example`.
> chat is available without authentication by default; login/register remain
> optional for tracking conversations, and admin ingest is not exposed in the
> frontend UI.

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
- `POST /api/auth/register` – create a user and return **access** + **refresh**
  tokens.  The request may include an `organization` field (string); if the
  named organization does not yet exist it will be created.  If omitted a
  per-user organization is generated automatically.  A token claim
  `org_id` is added to both access and refresh tokens.
- `POST /api/auth/login` – obtain access/refresh tokens for existing user.
- `POST /api/auth/refresh` – rotate a refresh token and receive a new access
  token (and new refresh token).
- `POST /api/auth/logout` – revoke a refresh token and prevent further use.
- `GET /api/auth/me` – returns current user info when authenticated, including
  `is_admin` and remaining `credits`.

JWT access tokens are short-lived (15 min by default) and use `SECRET_KEY`.
Tokens also carry an `org_id` claim which is used by the backend to enforce
strict tenant isolation.  Refresh tokens expire after 7 days (configurable
via settings) and are stored hashed in the database; only the raw token is
ever returned to clients.  Invalid or expired access/refresh tokens result
in a 401 response.  Tokens carry a `role` claim (`admin` for administrators)
as well as `org_id`.

#### Credit system
New users are granted 1000 credits by default. Each chat request consumes
credits equal to the number of tokens used (input + output) at the rate
specified in `MODEL_PRICING` settings. Credits and usage are deducted **only
after** a successful LLM response; if a query would drive the balance below
zero, a 402 `Payment Required` is returned after generation. Administrators
can view and adjust credit balances via the admin API.

### Chat & RAG
- `POST /api/chat/stream` – **protected endpoint requiring a valid JWT** and
  accepting `message` and optional `conversation_id`.
  * Saves user message to PostgreSQL.
  * Performs retrieval-augmented generation by embedding query via the
    locally-loaded `SentenceTransformer` model (`all-MiniLM-L6-v2`, 384‑dim),
    searching the FAISS index, and streaming a response from the Groq API.
  * Returns the new conversation id in the first SSE event along with a
    `context_meta` array describing which document chunks were retrieved.
  * Final SSE event includes a JSON object with the full answer and a
    `sources` list; footnotes are appended to the answer text.
  * Assistant replies saved to DB as well.
  * Embedding and retrieval timings are logged for observability.

> **Embedding dimension:** updated to 384 after switching from OpenAI.


### Admin
- `POST /api/admin/ingest` – ingest arbitrary text documents (admin only).
  Documents are tagged with the administrator's organization; searches and
  retrievals are limited to the current tenant.
  * Accepts a `file` field (PDF or plain text) and an optional `metadata`
    JSON string with `source`, `filename`, and `page` values.
  * Ingestion performs automatic chunking, embedding, and updates the FAISS
    index persistently; new columns are recorded in PostgreSQL.
  * The route currently expects multipart/form-data; JSON body ingestion
    will be re‑enabled soon.  This endpoint is **not linked from the frontend**
    by default.
- `GET /api/admin/users` – list registered users along with `credits`,
  `total_tokens_used`, and `total_cost`.
- `POST /api/admin/users/{user_id}/topup` – add credits to a user's account.
  This enables manual billing or promotional top‑ups.

### Database
- PostgreSQL database with tables for `organizations`, `users`,
  `conversations`, `messages`,
  `documents` and `document_chunks`.  The latter now includes `source`,
  `filename`, and `page` columns; see migration `0003_add_chunk_metadata.py`.
  Set `DATABASE_URL` appropriately; an example env file is provided.
- You can override `DATABASE_URL` to point at another database if desired.

#### Multi-tenancy
All user and conversation data is now scoped by `organization_id`.  Users
belongs to exactly one organization.  Admin APIs operate within the
caller’s organization unless the administrator’s account has no
`organization_id` (treating them as a super‑admin).  The `org_id` claim in
JWTs is used to inject the tenant context; a middleware populates
`request.state.organization_id` accordingly.
- SQLAlchemy ORM with session management in `app/db`.

### Vector Store
- FAISS used locally to store and query embeddings; hits now return
  associated metadata (`source`, `filename`, `page`).
- Embeddings generated locally using the `sentence-transformers/all-MiniLM-L6-v2` model.
- Index persisted to disk under configured `FAISS_DIR`.  If the database is cleared,
  stale index files are removed automatically on startup (see `app/main.py`).

### Frontend
- Next.js 14 App Router with pages for home, login/register, dashboard, and chat.
- Minimal responsive UI storing JWT in `localStorage` and streaming chat responses.

### Docker
- Compose file configures Postgres, backend, and frontend services with volumes.
  * During development the backend service also mounts `./backend/alembic` into
    the container so new migrations appear immediately; this was required to
    avoid `UndefinedTable` errors when adding the refresh tokens migration.
- Environment variables injected via `.env`.

### Environment Variables
- `GROQ_API_KEY`, `DATABASE_URL`, `SECRET_KEY`, and optional `FAISS_DIR`.
- `ADMIN_ORG` can be set to assign the seeded admin to a specific organization
  (omit for a global super-admin).  `DEFAULT_USER_ORG` controls the org of the
  default non-admin user created at startup.
- `ENV` determines the runtime environment (DEV, STAGING, PROD).  In production
  several security features are enabled automatically: HTTPS redirection,
  strict security headers, and more verbose request logging.  The application
  will still function if `ENV` is unset, defaulting to `DEV`.

#### Production deployment
The backend is packaged with a production-ready Dockerfile that launches
Gunicorn with Uvicorn workers.  Environment variables are read either from a
`.env` file (development) or from the host/provider environment (Render,
Railway, AWS, etc.).

Persistent storage for the FAISS directory (`FAISS_DIR`) is required so that
vector indexes survive restarts; when using Docker a volume such as
`faissdata` should be mounted.  The accompanying `docker-compose.yml` already
defines this for local development, and a `docker-compose.prod.yml` can be
constructed by removing the source mounts and `.env` references.

On startup the FastAPI application will automatically run any pending
Alembic migrations, create the FAISS directory, and load the index.  A
shutdown handler persists the index to disk.  Both `/health` (checks DB and
FAISS) and `/metrics` (Prometheus-compatible counters) are available by
default, making the service easy to monitor in production.

HTTPS enforcement works either via Starlette's `HTTPSRedirectMiddleware` or by
honoring the `X-Forwarded-Proto` header when the app is behind a TLS
terminator (common on cloud platforms).

To deploy on Render/Railway/AWS you generally:

1. Build or pull the Docker image using the provided `Dockerfile`.
2. Configure environment variables (DATABASE_URL, SECRET_KEY, GROQ_API_KEY,
   ENV=PROD, etc.) in the platform's settings.
3. Mount a persistent volume for the FAISS directory (`/app/faiss_data`).
4. Open port 8000 (or route traffic via the provider's load balancer).

Adjust workers (`-w`) and timeouts as necessary for your load profile.  The
current default (`2` workers) is suitable for low‑traffic demo deployments.


Termux / Android notes
----------------------
- This repository can be prepared for Termux-based development (Android) but
  building heavy native wheels (e.g. `torch`, `faiss`) on-device is often
  impractical. Recommended workflow:
  1. Run the included cleanup script to remove caches before packaging: `./scripts/clean_caches.sh`
  2. Install Python 3.11+ in Termux and `pip`.
  3. Install lightweight dependencies first (`pip install -r backend/requirements.txt`) and
    skip or replace heavy packages (Torch/FAISS) if they are unavailable; consider
    using a remote build machine or prebuilt wheels and copying the `backend` folder.
  4. For a reproducible small install on Termux, consider swapping to a smaller
    embedding model or using remote embeddings instead of local FAISS.

Cleaning caches
---------------
- To remove repository cache files and build artifacts before transferring to Termux run:

```bash
chmod +x ./scripts/clean_caches.sh
./scripts/clean_caches.sh
```

This removes `__pycache__`, `*.pyc`, frontend `.next` and `node_modules` folders.

**Deployment/CI notes:**
- Ensure `.env` values are provided in your deployment environment;
  the backend reads them via `python-dotenv` (through `settings`).
- Persistent storage for the FAISS directory is required so that the vector index
  survives restarts.

# aadya.nexora

---

© 2026 Aidni Global LLP. All rights reserved.
Application designed, architected and developed by Hardikkumar Gajjar.