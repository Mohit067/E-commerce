"""Agent API: persistent conversations + streaming chat (SSE)."""
import asyncio
import json
import uuid
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ... import models
from ...database import get_db
from ...deps import get_current_user, get_optional_user
from ...schemas import AgentChatIn
from ...agents.root_agent import run_agent_turn

router = APIRouter()


def _get_or_create_conv(db: Session, user, cid: str | None, first_msg: str):
    if cid:
        c = db.get(models.AgentConversation, cid)
        if c and (c.user_id is None or not user or c.user_id == user.id):
            return c
    c = models.AgentConversation(id=cid or str(uuid.uuid4()),
                                 user_id=user.id if user else None,
                                 title=(first_msg[:60] or "Shopping chat"))
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _history(db: Session, conv_id: str):
    return db.query(models.AgentMessage).filter_by(conversation_id=conv_id).order_by(
        models.AgentMessage.created_at).all()


@router.post("/chat", summary="Chat with shopping agent (non-streaming)")
def chat(data: AgentChatIn, db: Session = Depends(get_db), user=Depends(get_optional_user)):
    conv = _get_or_create_conv(db, user, data.conversation_id, data.message)
    db.add(models.AgentMessage(conversation_id=conv.id, role="user", content=data.message))
    db.commit()
    reply, products = run_agent_turn(db, conv, user, data.message)
    db.add(models.AgentMessage(conversation_id=conv.id, role="assistant", content=reply,
                               product_refs=json.dumps([p["id"] for p in products])))
    db.commit()
    return {"conversation_id": conv.id, "reply": reply, "products": products}


@router.post("/chat/stream", summary="Streaming chat (SSE)")
def chat_stream(data: AgentChatIn, db: Session = Depends(get_db), user=Depends(get_optional_user)):
    conv = _get_or_create_conv(db, user, data.conversation_id, data.message)
    db.add(models.AgentMessage(conversation_id=conv.id, role="user", content=data.message))
    db.commit()
    reply, products = run_agent_turn(db, conv, user, data.message)
    db.add(models.AgentMessage(conversation_id=conv.id, role="assistant", content=reply,
                               product_refs=json.dumps([p["id"] for p in products])))
    db.commit()

    async def gen():
        yield f"data: {json.dumps({'type': 'start', 'conversation_id': conv.id})}\n\n"
        # progressive token streaming (word chunks)
        buf = ""
        for word in reply.split(" "):
            buf += word + " "
            if len(buf) > 24:
                yield f"data: {json.dumps({'type': 'token', 'token': buf})}\n\n"
                buf = ""
                await asyncio.sleep(0.015)
        if buf:
            yield f"data: {json.dumps({'type': 'token', 'token': buf})}\n\n"
        yield f"data: {json.dumps({'type': 'products', 'products': products})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'conversation_id': conv.id})}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@router.get("/conversations", summary="My conversations")
def list_convs(db: Session = Depends(get_db), user=Depends(get_current_user)):
    cs = db.query(models.AgentConversation).filter_by(user_id=user.id).order_by(
        models.AgentConversation.updated_at.desc()).limit(50).all()
    return [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in cs]


@router.get("/conversations/{cid}", summary="Conversation history")
def get_conv(cid: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    c = db.get(models.AgentConversation, cid)
    if not c or c.user_id != user.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Conversation not found")
    return [{"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at}
            for m in _history(db, cid)]
