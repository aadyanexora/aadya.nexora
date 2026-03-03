from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from app.core.security import decode_access_token
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.chat import Conversation, Message
from app.models.user import User
from app.models.document import Document
from app.models.usage_log import UsageLog
from app.services.openai_service import OpenAIService
from app.services.rag_service import RAGService
import json
import time

# rate limiter import
from slowapi import Limiter
from fastapi import Request

router = APIRouter()
limiter = Limiter(key_func=lambda request: request.client.host)


class ChatIn(BaseModel):
    message: str
    conversation_id: Optional[int] = None


def get_current_user_optional(authorization: str = Header(None)):
    # if token provided, decode it; otherwise return None
    if not authorization:
        return None
    try:
        token = authorization.split(" ")[-1]
        data = decode_access_token(token)
        return data.get("sub")
    except Exception:
        return None


@router.post("/stream")
@limiter.limit("10/minute")
def chat_stream(
    request: Request,
    payload: ChatIn, db: Session = Depends(get_db), user_id: Optional[str] = Depends(get_current_user_optional)
):
    # Ensure conversation
    conv_id = payload.conversation_id
    if not conv_id:
        # when there is no user, store user_id as None or 0
        conv = Conversation(user_id=int(user_id) if user_id else None)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

    # Save user message
    user_msg = Message(
        conversation_id=conv_id,
        user_id=int(user_id) if user_id else None,
        role="user",
        content=payload.message,
    )
    db.add(user_msg)
    db.commit()

    # gather last 10 messages for context
    history_msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.created_at.desc())
        .limit(10)
        .all()
    )
    history_texts = [m.content for m in reversed(history_msgs)]

    rag = RAGService()
    hits = rag.search(payload.message, top_k=5)
    # hits -> list of (chunk_content, doc_id, chunk_index, score)

    contexts: List[str] = []
    if history_texts:
        contexts.extend(history_texts)
    chunk_meta = []
    for text, doc_id, chunk_idx, score in hits:
        contexts.append(f"[doc {doc_id} chunk {chunk_idx}] {text}")
        chunk_meta.append({"doc_id": doc_id, "chunk_index": chunk_idx, "score": score})

    # build structured citations list before streaming
    citations = []
    if hits:
        # fetch document titles
        doc_ids = list({doc_id for _, doc_id, _, _ in hits})
        docs = {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}
        for text, doc_id, chunk_idx, score in hits:
            doc = docs.get(doc_id)
            citations.append(
                {
                    "document_id": doc_id,
                    "document_title": doc.name if doc else None,
                    "chunk_index": chunk_idx,
                    "snippet": (text[:300] + "...") if len(text) > 300 else text,
                }
            )

    openai = OpenAIService()
    # measure execution time for the generation
    start_ts = time.time()
    assistant_text, tokens_used = openai.chat_with_context(payload.message, contexts)
    elapsed_ms = int((time.time() - start_ts) * 1000)

    # persist assistant message
    assistant_msg = Message(
        conversation_id=conv_id, user_id=0, role="assistant", content=assistant_text
    )
    db.add(assistant_msg)
    db.commit()

    # deduct credits if user present
    try:
        if user_id:
            u = db.query(User).filter(User.id == int(user_id)).first()
            if u:
                if (u.credits or 0) <= 0:
                    return JSONResponse(status_code=402, content={"detail": "Insufficient credits"})
                u.credits = (u.credits or 0) - 1
                db.add(u)
                db.commit()
    except Exception:
        # don't fail the request on credit bookkeeping errors
        db.rollback()

    # log usage
    try:
        ul = UsageLog(
            user_id=int(user_id) if user_id else None,
            endpoint="/api/chat/stream",
            tokens_used=tokens_used,
            response_time_ms=elapsed_ms,
        )
        db.add(ul)
        db.commit()
    except Exception:
        db.rollback()

    def event_stream():
        # send conversation id for client to associate
        yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"
        # also include context metadata for backward compatibility
        yield f"data: {json.dumps({'context_meta': chunk_meta})}\n\n"
        for chunk in openai.stream_chat_with_context(payload.message, contexts):
            yield f"data: {chunk}\n\n"

        # final structured citation payload (kept at end)
        final = {"answer": assistant_text, "sources": citations}
        yield f"data: {json.dumps(final)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations")
def list_conversations(user_id: Optional[str] = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    # return all conversations if no user; otherwise filter
    query = db.query(Conversation)
    if user_id:
        query = query.filter(Conversation.user_id == int(user_id))
    convs = query.all()
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in convs
    ]


@router.get("/history/{conv_id}")
def get_history(
    conv_id: int, user_id: Optional[str] = Depends(get_current_user_optional), db: Session = Depends(get_db)
):
    msgs = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.created_at)
        .all()
    )
    return [
        {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
        for m in msgs
    ]
