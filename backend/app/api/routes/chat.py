from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from app.core.security import decode_access_token
from app.db.session import get_db
from sqlalchemy.orm import Session
from app.models.chat import Conversation, Message
from app.services.openai_service import OpenAIService
from app.services.rag_service import RAGService

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
def chat_stream(payload: ChatIn, db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    # Ensure conversation
    conv_id = payload.conversation_id
    if not conv_id:
        conv = Conversation(user_id=int(user_id))
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

    # Save user message
    user_msg = Message(conversation_id=conv_id, user_id=int(user_id), role="user", content=payload.message)
    db.add(user_msg)
    db.commit()

    rag = RAGService()
    contexts = rag.search(payload.message, top_k=3)

    openai = OpenAIService()

    def event_stream():
        for chunk in openai.stream_chat_with_context(payload.message, contexts):
            # Save assistant chunk as messages progressively is optional; we'll save final below
            yield f"data: {chunk}\n\n"

    # Call OpenAI to generate full assistant message (non-stream) to store in DB
    assistant_text = openai.chat_with_context(payload.message, contexts)
    assistant_msg = Message(conversation_id=conv_id, user_id=0, role="assistant", content=assistant_text)
    db.add(assistant_msg)
    db.commit()

    return StreamingResponse(event_stream(), media_type="text/event-stream")
