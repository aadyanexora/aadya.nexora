from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from app.services.ingestion_service import IngestionService
from app.core.security import decode_access_token

router = APIRouter()


class IngestIn(BaseModel):
    texts: List[str]


def admin_required(authorization: str = Depends(lambda: None)):
    # Simple admin check placeholder. In production, check user's is_admin flag.
    return True


@router.post("/ingest")
def ingest(payload: IngestIn, auth: bool = Depends(admin_required)):
    if not auth:
        raise HTTPException(status_code=403, detail="Admin required")
    service = IngestionService()
    service.ingest_texts(payload.texts)
    return {"status": "ok", "ingested": len(payload.texts)}
