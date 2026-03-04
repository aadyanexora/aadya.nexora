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
from fastapi import Request
from app.core.config import settings

# shared limiter instance
from app.core.limiter import limiter

router = APIRouter()


class ChatIn(BaseModel):
    message: str
    conversation_id: Optional[int] = None


def get_current_user_optional(authorization: str = Header(None)):
    # if token provided decode it; otherwise return None
    if not authorization:
        return None
    try:
        token = authorization.split(" ")[-1]
        data = decode_access_token(token)
        return data
    except Exception:
        return None


def get_current_user(request: Request, authorization: str = Header(...)) -> dict:
    """Dependency that returns the decoded token payload.

    Raises a 401 HTTPException if the header is missing or the token is invalid.
    Also stores numeric ``user_id`` and ``organization_id`` on the request state for
    downstream code (rate limiting, tenant filtering).
    """
    token = authorization.split(" ")[-1]
    data = decode_access_token(token)  # will raise 401 on failure
    # attempt to parse numeric id for convenience
    try:
        uid = int(data.get("sub"))
    except Exception:
        uid = None
    request.state.user_id = uid
    request.state.organization_id = data.get("org_id")
    return data


def _parse_user_id(sub: str | None) -> int | None:
    """Return integer ID if ``sub`` looks numeric, otherwise ``None``."""
    if not sub:
        return None
    try:
        return int(sub)
    except (ValueError, TypeError):
        return None


@router.post("/stream")
@limiter.limit("10/minute")
def chat_stream(
    request: Request,
    payload: ChatIn,
    db: Session = Depends(get_db),
    user_payload: dict = Depends(get_current_user),
):
    # parse user id once
    user_id = _parse_user_id(user_payload.get("sub")) if user_payload else None
    org_id = user_payload.get("org_id") if user_payload else None
    # Ensure conversation
    conv_id = payload.conversation_id
    if conv_id:
        # verify tenant ownership
        conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        if org_id is not None and conv.organization_id != org_id:
            raise HTTPException(status_code=403, detail="Access denied")
    if not conv_id:
        # when there is no conversation, create one; use parsed user id and org
        conv = Conversation(user_id=user_id, organization_id=org_id)
        db.add(conv)
        db.commit()
        db.refresh(conv)
        conv_id = conv.id

    # Save user message
    user_msg = Message(
        conversation_id=conv_id,
        user_id=_parse_user_id(user_payload.get("sub")) if user_payload else None,
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
    hits = rag.search(payload.message, top_k=5, org_id=org_id)
    # hits -> list of dicts with content, document_id, chunk_index, score, source, filename, page

    contexts: List[str] = []
    if history_texts:
        contexts.extend(history_texts)
    chunk_meta = []
    for h in hits:
        contexts.append(h["content"])
        chunk_meta.append(
            {
                "document_id": h["document_id"],
                "chunk_index": h["chunk_index"],
                "score": h["score"],
                "source": h.get("source"),
                "filename": h.get("filename"),
                "page": h.get("page"),
            }
        )

    # build structured citations list before streaming
    citations = []
    if hits:
        for idx, h in enumerate(hits, start=1):
            citations.append(
                {
                    "id": idx,
                    "source": h.get("source"),
                    "filename": h.get("filename"),
                    "page": h.get("page"),
                    "score": h.get("score"),
                    "snippet": (h["content"][:300] + "...") if len(h["content"]) > 300 else h["content"],
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

    # credit bookkeeping and usage logging happen only after generation succeeded
    if user_id:
        try:
            u = db.query(User).filter(User.id == user_id).first()
            if u:
                # compute cost based on pricing configuration
                cost_per = settings.MODEL_PRICING.get(openai.chat_model, 0.0)
                cost = (tokens_used or 0) * cost_per

                # ensure enough credits remain
                remaining = (u.credits or 0) - (tokens_used or 0)
                if remaining < 0:
                    return JSONResponse(status_code=402, content={"detail": "Insufficient credits"})

                # deduct tokens and update aggregates
                u.credits = remaining
                u.total_tokens_used = (u.total_tokens_used or 0) + (tokens_used or 0)
                u.total_cost = (u.total_cost or 0) + cost
                db.add(u)
                db.commit()

                # log the usage event
                try:
                    ul = UsageLog(
                        user_id=user_id,
                        tokens_used=tokens_used,
                        cost=cost,
                        model_name=openai.chat_model,
                        organization_id=org_id,
                    )
                    db.add(ul)
                    db.commit()
                except Exception:
                    db.rollback()
        except Exception:
            # don't let bookkeeping failures break the chat flow
            db.rollback()
    else:
        # log anonymous usage as well (no user_id)
        try:
            cost_per = settings.MODEL_PRICING.get(openai.chat_model, 0.0)
            cost = (tokens_used or 0) * cost_per
            ul = UsageLog(
                user_id=None,
                tokens_used=tokens_used,
                cost=cost,
                model_name=openai.chat_model,
                organization_id=org_id,
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
        # append numbered footnotes to the answer text
        answer_text = assistant_text
        if citations:
            footnotes = []
            for c in citations:
                label = c.get('source') or c.get('filename') or 'unknown'
                page = c.get('page')
                if page is not None:
                    label = f"{label} Page {page}"
                footnotes.append(f"[{c['id']}] {label}")
            answer_text = answer_text + "\n\n" + "\n".join(footnotes)
        final = {"answer": answer_text, "sources": citations}
        yield f"data: {json.dumps(final)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/conversations")
def list_conversations(
    user_payload: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    # return all conversations if anonymous; otherwise restrict to the
    # user's organization (and optionally to their own contributions).
    query = db.query(Conversation)
    if user_payload:
        org = user_payload.get("org_id")
        if org is not None:
            query = query.filter(Conversation.organization_id == org)
        # also optionally show only those started by this user
        try:
            uid = int(user_payload.get("sub"))
        except Exception:
            uid = None
        if uid is not None:
            query = query.filter(Conversation.user_id == uid)
    convs = query.all()
    return [
        {"id": c.id, "title": c.title, "created_at": c.created_at.isoformat()}
        for c in convs
    ]


@router.get("/history/{conv_id}")
def get_history(
    conv_id: int,
    user_payload: Optional[dict] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    # ensure conversation belongs to the same organization as caller (if any)
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if user_payload:
        org = user_payload.get("org_id")
        if org is not None and conv.organization_id != org:
            raise HTTPException(status_code=403, detail="Access denied")
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
