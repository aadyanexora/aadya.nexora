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


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
