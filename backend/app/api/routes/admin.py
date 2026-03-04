from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Request, Body
from io import BytesIO

# optional import for PDF support; will be None if library missing
try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None
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
    # compute simple usage metrics
    avg_cost = db.query(func.avg(UsageLog.cost)).scalar() or 0
    # requests in last 24h
    from datetime import datetime, timedelta
    cutoff = datetime.utcnow() - timedelta(hours=24)
    total_requests_24h = db.query(func.count(UsageLog.id)).filter(UsageLog.created_at >= cutoff).scalar() or 0

    return {
        "total_users": int(total_users),
        "total_conversations": int(total_conversations),
        "total_messages": int(total_messages),
        "avg_cost_per_request": float(avg_cost) if avg_cost is not None else 0.0,
        "total_requests_24h": int(total_requests_24h),
    }


class IngestIn(BaseModel):
    texts: Optional[List[str]] = None


@router.post("/ingest")
async def ingest(
    request: Request,
    files: Optional[List[UploadFile]] = File(None),
    user: User = Depends(admin_required),
):
    # read multipart/form-data for texts
    import logging, traceback
    logger = logging.getLogger(__name__)
    try:
        texts: Optional[List[str]] = None
        form = await request.form()
        logger.info(f"form keys: {list(form.keys())}")
        if "texts" in form:
            values = []
            for key, val in form.multi_items():
                if key == "texts":
                    values.append(val)
            texts = values or None
        logger.info(f"parsed texts from form: {texts}")

        # assemble structured documents list for ingestion service
        docs: List[dict] = []
        if texts:
            for t in texts:
                docs.append({"text": t, "source": None, "filename": None, "page": None})

        # process files
        if files:
            for f in files:
                filename = f.filename
                lower = filename.lower()
                data = await f.read()
                if lower.endswith(".pdf") and PdfReader is not None:
                    try:
                        reader = PdfReader(BytesIO(data))
                        for page_no, page in enumerate(reader.pages, start=1):
                            txt = page.extract_text() or ""
                            docs.append({"text": txt, "source": filename, "filename": filename, "page": page_no})
                    except Exception as e:
                        raise HTTPException(status_code=400, detail=f"PDF parsing failed: {e}")
                else:
                    try:
                        txt = data.decode("utf-8")
                    except Exception:
                        txt = data.decode("latin-1", errors="ignore")
                    docs.append({"text": txt, "source": filename, "filename": filename, "page": None})

        if not docs:
            raise HTTPException(status_code=400, detail="No content provided")

        service = IngestionService()
        service.ingest_documents(docs)
        return {"status": "ok", "ingested": len(docs)}

    except Exception as exc:
        logger.error("ingest route failed: %s", traceback.format_exc())
        raise

    # file uploads: support PDF, TXT, raw text
    if files:
        for f in files:
            filename = f.filename
            lower = filename.lower()
            data = await f.read()
            if lower.endswith(".pdf") and PdfReader is not None:
                # extract text page by page
                try:
                    reader = PdfReader(BytesIO(data))
                    for page_no, page in enumerate(reader.pages, start=1):
                        txt = page.extract_text() or ""
                        docs.append({"text": txt, "source": filename, "filename": filename, "page": page_no})
                except Exception as e:
                    raise HTTPException(status_code=400, detail=f"PDF parsing failed: {e}")
            else:
                # treat as simple text
                try:
                    txt = data.decode("utf-8")
                except Exception:
                    txt = data.decode("latin-1", errors="ignore")
                docs.append({"text": txt, "source": filename, "filename": filename, "page": None})

    if not docs:
        raise HTTPException(status_code=400, detail="No content provided")

    service = IngestionService()
    service.ingest_documents(docs)
    return {"status": "ok", "ingested": len(docs)}


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


class UserOut(BaseModel):
    id: int
    email: str
    is_admin: bool
    credits: int
    total_tokens_used: int
    total_cost: float
    created_at: str


class TopUpIn(BaseModel):
    amount: int


@router.get('/users')
def list_users(user: User = Depends(admin_required), db: Session = Depends(get_db)):
    """Admin-only endpoint to return all registered users with credit info."""
    users = db.query(User).all()
    return [
        UserOut(
            id=u.id,
            email=u.email,
            is_admin=u.is_admin,
            credits=u.credits or 0,
            total_tokens_used=u.total_tokens_used or 0,
            total_cost=float(u.total_cost or 0),
            created_at=u.created_at.isoformat(),
        ).dict()
        for u in users
    ]


@router.post('/users/{user_id}/topup')
def topup_user(
    user_id: int,
    payload: TopUpIn,
    admin: User = Depends(admin_required),
    db: Session = Depends(get_db),
):
    """Add credits to a specific user account."""
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u.credits = (u.credits or 0) + payload.amount
    db.add(u)
    db.commit()
    return {"id": u.id, "new_credits": u.credits}
