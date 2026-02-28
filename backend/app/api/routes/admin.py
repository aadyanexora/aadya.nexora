from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel, root_validator
from typing import List, Optional, Tuple
from app.services.ingestion_service import IngestionService
from app.core.security import decode_access_token
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.user import User

router = APIRouter()


class IngestIn(BaseModel):
    texts: Optional[List[str]] = None


def admin_required(
    authorization: str = Header(None), db: Session = Depends(get_db)
) -> User:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.split(" ")[-1]
    data = decode_access_token(token)
    user_id = data.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin required")
    return user


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
