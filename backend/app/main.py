from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db import session as db_session
from app.api import auth, chat, admin
import logging
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import uuid

# basic structured logging configuration
logging.basicConfig(
    format="%(asctime)s %(levelname)s [%(request_id)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# prometheus metrics
REQUEST_COUNT = Counter("app_requests_total", "Total HTTP requests", ["method", "endpoint"])
REQUEST_LATENCY = Histogram("app_request_latency_seconds", "Request latency", ["endpoint"])

app = FastAPI(title="Aadya - Nexora AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.on_event("startup")
def on_startup():
    # Create DB tables
    from app.db import base
    # import all models so they are registered on the metadata
    import app.models.user
    import app.models.document
    import app.models.chat

    base.Base.metadata.create_all(bind=db_session.engine)
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
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
