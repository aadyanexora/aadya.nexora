from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel, root_validator
from typing import List, Optional, Tuple
from app.services.ingestion_service import IngestionService
from app.core.security import decode_access_token
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.dependencies import admin_required

router = APIRouter()

@router.get('/analytics/summary')
def analytics_summary(user: User = Depends(admin_required), db: Session = Depends(get_db)):
    from sqlalchemy import func
    from app.models.chat import Conversation, Message
    from app.models.usage_log import UsageLog

    total_users = db.query(func.count(User.id)).scalar() or 0
    total_conversations = db.query(func.count(Conversation.id)).scalar() or 0
    total_messages = db.query(func.count(Message.id)).scalar() or 0
    avg_response_time = db.query(func.avg(UsageLog.response_time_ms)).scalar() or 0
    # requests in last 24h
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)
    total_requests_24h = db.query(func.count(UsageLog.id)).filter(UsageLog.created_at >= cutoff).scalar() or 0

    return {
        "total_users": int(total_users),
        "total_conversations": int(total_conversations),
        "total_messages": int(total_messages),
        "avg_response_time": float(avg_response_time) if avg_response_time is not None else 0.0,
        "total_requests_24h": int(total_requests_24h),
    }


class IngestIn(BaseModel):
    texts: Optional[List[str]] = None


@router.post("/ingest")
async def ingest(
    texts: Optional[List[str]] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    user: User = Depends(admin_required),
):
    # gather all strings to ingest
    to_process: List[str] = []
    names: List[str] = []
    if texts:
        to_process.extend(texts)
        names.extend([None] * len(texts))
    if files:
        for f in files:
            content = (await f.read()).decode("utf-8")
            to_process.append(content)
            names.append(f.filename)
    if not to_process:
        raise HTTPException(status_code=400, detail="No content provided")

    service = IngestionService()
    service.ingest_texts(to_process, names)
    return {"status": "ok", "ingested": len(to_process)}


@router.get("/documents")
def list_documents(user: User = Depends(admin_required), db: Session = Depends(get_db)):
    from app.models.document import Document, DocumentChunk
    docs = db.query(Document).all()
    out = []
    for d in docs:
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == d.id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )
        out.append(
            {
                "id": d.id,
                "name": d.name,
                "chunk_count": len(chunks),
                "chunks": [
                    {"id": c.id, "index": c.chunk_index} for c in chunks
                ],
            }
        )
    return out


@router.get('/users')
def list_users(user: User = Depends(admin_required), db: Session = Depends(get_db)):
    """Admin-only endpoint to return all registered users."""
    users = db.query(User).all()
    return [
        {"id": u.id, "email": u.email, "is_admin": u.is_admin, "created_at": u.created_at.isoformat()} 
        for u in users
    ]
