from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db import session as db_session
from app.api import auth, chat, admin

app = FastAPI(title="Aadya - Nexora AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    from app.models.user import User
    from app.core.security import hash_password
    from sqlalchemy.orm import Session

    db: Session = db_session.SessionLocal()
    try:
        admin_email = "hardik@aidniglobal.com"
        admin_password = "Gaatha@1805"
        existing = db.query(User).filter(User.email == admin_email).first()
        if not existing:
            admin = User(
                email=admin_email,
                hashed_password=hash_password(admin_password),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            print(f"[startup] created super admin {admin_email}")
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
                    print(f"[startup] removed stale file {p}")
    finally:
        db2.close()


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
