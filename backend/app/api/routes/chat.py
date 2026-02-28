from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from app.core.security import decode_access_token
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.chat import Conversation, Message
from app.services.openai_service import OpenAIService
from app.services.rag_service import RAGService
import json

router = APIRouter()


class ChatIn(BaseModel):
    message: str
    conversation_id: Optional[int] = None


def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.split(" ")[-1]
    data = decode_access_token(token)
    return data.get("sub")


@router.post("/stream")
def chat_stream(
    payload: ChatIn, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)
):
    # Ensure conversation
    conv_id = payload.conversation_id
    if not conv_id:
        conv = Conversation(user_id=int(user_id))
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

    # Save user message
    user_msg = Message(
        conversation_id=conv_id, user_id=int(user_id), role="user", content=payload.message
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

    openai = OpenAIService()

    def event_stream():
        # send metadata events first
        yield f"data: {json.dumps({'conversation_id': conv_id})}\n\n"
        yield f"data: {json.dumps({'context_meta': chunk_meta})}\n\n"
        for chunk in openai.stream_chat_with_context(payload.message, contexts):
            yield f"data: {chunk}\n\n"

    assistant_text = openai.chat_with_context(payload.message, contexts)
    assistant_msg = Message(
        conversation_id=conv_id, user_id=0, role="assistant", content=assistant_text
    )
    db.add(assistant_msg)
    db.commit()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations")
def list_conversations(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = db.query(Conversation).filter(Conversation.user_id == int(user_id)).all()
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in convs
    ]


@router.get("/history/{conv_id}")
def get_history(
    conv_id: int, user_id: str = Depends(get_current_user), db: Session = Depends(get_db)
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
