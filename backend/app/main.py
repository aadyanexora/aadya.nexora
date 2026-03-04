from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.config import settings
from app.db import session as db_session
from app.core.security import decode_access_token
from app.api import auth, chat, admin
# new admin login router sits separately
from app.routers import admin_auth

# bring in centralized logging
from app.core.logging import get_logger
import time
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
import uuid
import os

# local vector store class for health/startup/shutdown
from app.rag.vector_store import FaissVectorStore

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
allow_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# custom HTTPS enforcement middleware that respects the current environment
# variable; we can't rely on adding the middleware only when the module is
# imported because tests can flip `settings.ENV` at runtime.
@app.middleware("http")
async def enforce_https(request: Request, call_next):
    if settings.is_production:
        scheme = request.url.scheme
        # honor X-Forwarded-Proto from load balancers
        if scheme != "https" and request.headers.get("x-forwarded-proto", "").lower() != "https":
            url = request.url.replace(scheme="https")
            return Response(status_code=307, headers={"Location": str(url)})
    return await call_next(request)

# security headers to harden responses
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.update({
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
            "Permissions-Policy": "geolocation=(), microphone=()",
            "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        })
        return response

app.add_middleware(SecurityHeadersMiddleware)


@app.middleware("http")
async def extract_org(request: Request, call_next):
    # parse Authorization header early so downstream handlers can rely on
    # ``request.state.organization_id``.  We don't raise on failure; the
    # normal dependencies will still enforce auth where required.
    auth = request.headers.get("Authorization")
    request.state.organization_id = None
    request.state.user_id = None
    if auth:
        try:
            token = auth.split(" ")[-1]
            data = decode_access_token(token)
            request.state.organization_id = data.get("org_id")
            try:
                request.state.user_id = int(data.get("sub"))
            except Exception:
                request.state.user_id = None
        except Exception:
            # invalid token; simply don't populate state
            pass
    return await call_next(request)

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
    # structured log for every request
    logger.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency": latency,
            "client": request.client.host if request.client else None,
            "env": settings.ENV,
        },
    )
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
    # basic checks: DB connectivity and FAISS index availability
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
        # check that FAISS dir exists and index can be loaded
        fdir = settings.FAISS_DIR
        details["faiss_dir_exists"] = os.path.exists(fdir)
        if details["faiss_dir_exists"]:
            # try to instantiate the vector store; this will create an empty
            # index if none is present.
            store = FaissVectorStore()
            details["faiss_index_size"] = store.index.ntotal
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
        # super-admin seeding (organization assignment optional via ADMIN_ORG env)
        admin_email = settings.ADMIN_EMAIL
        admin_password = settings.ADMIN_PASSWORD
        org_id = None
        org_name = getattr(settings, "ADMIN_ORG", None)
        if org_name:
            from app.models.organization import Organization
            org = db.query(Organization).filter(Organization.name == org_name).first()
            if not org:
                org = Organization(name=org_name)
                db.add(org)
                db.commit()
                db.refresh(org)
            org_id = org.id
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            admin = User(
                email=admin_email,
                hashed_password=hash_password(admin_password),
                is_admin=True,
                organization_id=org_id,
            )
            db.add(admin)
            db.commit()
            logger.info(f"[startup] created super admin {admin_email}", extra={"request_id": request_id if False else ""})
        else:
            existing.organization_id = org_id
            db.add(existing)
            db.commit()

        # default non-admin user for testing
        default_email = getattr(settings, "DEFAULT_USER_EMAIL", None) or "user@example.com"
        default_password = getattr(settings, "DEFAULT_USER_PASSWORD", None) or "password"
        default_org = getattr(settings, "DEFAULT_USER_ORG", None) or f"org-{default_email}"
        if not db.query(User).filter(User.email == default_email).first():
            # create default organization if requested
            if default_org:
                from app.models.organization import Organization
                org2 = db.query(Organization).filter(Organization.name == default_org).first()
                if not org2:
                    org2 = Organization(name=default_org)
                    db.add(org2)
                    db.commit()
                    db.refresh(org2)
                default_org_id = org2.id
            else:
                default_org_id = None
            user = User(
                email=default_email,
                hashed_password=hash_password(default_password),
                is_admin=False,
                organization_id=default_org_id,
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

    # load FAISS index now so that any errors surface immediately and the
    # object can be re-used later; store on app state for shutdown persist.
    try:
        app.state.vector_store = FaissVectorStore()
        logger.info("[startup] faiss index loaded", extra={"request_id": ""})
    except Exception as e:
        logger.warning(f"unable to load faiss index on startup: {e}")


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
# admin router for analytics/ingest/document management
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
# simple admin login endpoint (for tooling/testing) at /admin/login
app.include_router(admin_auth.router, prefix="/admin", tags=["admin"])


@app.on_event("shutdown")
def on_shutdown():
    # persist FAISS index if we've loaded one
    vs = getattr(app.state, "vector_store", None)
    if vs:
        try:
            vs._persist()
            logger.info("[shutdown] faiss index persisted", extra={"request_id": ""})
        except Exception as e:
            logger.warning(f"error persisting faiss index on shutdown: {e}")
    # close DB connections if any (SQLAlchemy will handle teardown automatically)

