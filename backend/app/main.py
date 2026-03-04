from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db import session as db_session
from app.api import auth, chat, admin
# new admin login router sits separately
from app.routers import admin_auth

# bring in centralized logging
from app.core.logging import get_logger
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import uuid

# rate limiting
from app.core.limiter import limiter

logger = get_logger(__name__)

# prometheus metrics
REQUEST_COUNT = Counter("app_requests_total", "Total HTTP requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("app_request_latency_seconds", "Request latency", ["endpoint"])

# limiter is already configured in core/limiter and imported above

app = FastAPI(title="Aadya - Nexora AI")

# SlowAPI rate limiter middleware
from slowapi.middleware import SlowAPIMiddleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(429, lambda request, exc: Response("Too many requests", status_code=429))

# configure CORS from settings (defaults to localhost dev origin)
from app.core.config import settings
allow_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_id_and_metrics(request: Request, call_next):
    request_id = str(uuid.uuid4())
    # attach to logging context
    request.state.request_id = request_id
    start = time.time()
    response = await call_next(request)
    latency = time.time() - start
    REQUEST_COUNT.labels(request.method, request.url.path).inc()
    REQUEST_LATENCY.labels(request.url.path).observe(latency)
    response.headers["X-Request-ID"] = request_id
    return response


@app.middleware("http")
async def log_failed_auth(request: Request, call_next):
    response = await call_next(request)
    if response.status_code == 401:
        logger.warning(
            "authentication failure",
            extra={
                "path": request.url.path,
                "client": request.client.host,
                "request_id": getattr(request.state, "request_id", ""),
            },
        )
    return response


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    # basic checks: DB connectivity and FAISS dir
    ok = True
    details = {}
    try:
        from sqlalchemy import text
        db = db_session.SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        details["db"] = "ok"
    except Exception as e:
        ok = False
        details["db"] = f"error: {str(e)}"

    try:
        import os
        fdir = settings.FAISS_DIR
        details["faiss_dir_exists"] = os.path.exists(fdir)
        ok = ok and details["faiss_dir_exists"]
    except Exception as e:
        ok = False
        details["faiss"] = f"error: {str(e)}"

    return {"status": "ok" if ok else "error", "details": details}


@app.on_event("startup")
def on_startup():
    # run alembic migrations so tables are available before anything else
    try:
        from alembic import command
        from alembic.config import Config
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        logger.warning(f"could not run migrations on startup: {e}")

    # Ensure FAISS dir exists
    import os

    os.makedirs(settings.FAISS_DIR, exist_ok=True)

    # ==== Super-admin seeding ====
    # create a default administrator if it doesn't already exist
    # credentials come from settings so they can be overridden via env/.env
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy.orm import Session

    db: Session = db_session.SessionLocal()
    try:
        # super-admin seeding
        admin_email = settings.ADMIN_EMAIL
        admin_password = settings.ADMIN_PASSWORD
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            admin = User(
                email=admin_email,
                hashed_password=hash_password(admin_password),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            logger.info(f"[startup] created super admin {admin_email}", extra={"request_id": request_id if False else ""})

        # default non-admin user for testing
        default_email = getattr(settings, "DEFAULT_USER_EMAIL", None) or "user@example.com"
        default_password = getattr(settings, "DEFAULT_USER_PASSWORD", None) or "password"
        if not db.query(User).filter(User.email == default_email).first():
            user = User(
                email=default_email,
                hashed_password=hash_password(default_password),
                is_admin=False,
            )
            db.add(user)
            db.commit()
            logger.info(f"[startup] created default user {default_email}", extra={"request_id": request_id if False else ""})
    finally:
        db.close()

    # ==== FAISS cleanup ====
    # if the database has been reset (no documents) but the index files remain,
    # remove them so a fresh index will be built later. this avoids stale data
    # persisting across resets.
    from app.db.session import get_db
    from app.models.document import Document

    db2: Session = db_session.SessionLocal()
    try:
        doc_count = db2.query(Document).count()
        if doc_count == 0:
            # no documents, delete any existing index files
            idx_path = os.path.join(settings.FAISS_DIR, "index.faiss")
            map_path = os.path.join(settings.FAISS_DIR, "mapping.pkl")
            for p in (idx_path, map_path):
                if os.path.exists(p):
                    os.remove(p)
                    logger.info(f"[startup] removed stale file {p}")
    finally:
        db2.close()


@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
# admin router for analytics/ingest/document management
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
# simple admin login endpoint (for tooling/testing) at /admin/login
app.include_router(admin_auth.router, prefix="/admin", tags=["admin"])
