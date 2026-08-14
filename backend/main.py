import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from backend import agent, conversations
from backend.db import get_session, init_db
from backend.schemas import ApprovalRequest, ConversationCreateRequest, MessageRequest


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI Agent Workbench", lifespan=lifespan)


def _conversation_dict(c) -> dict:
    return {"id": c.id, "title": c.title, "status": c.status}


def _message_dict(m) -> dict:
    return {"role": m.role, "content": m.content}


@app.get("/conversations")
async def list_conversations():
    session = get_session()
    try:
        return [_conversation_dict(c) for c in conversations.list_conversations(session)]
    finally:
        session.close()


@app.post("/conversations")
async def create_conversation(request: ConversationCreateRequest):
    session = get_session()
    try:
        conversation = conversations.create_conversation(session, request.title)
        return _conversation_dict(conversation)
    finally:
        session.close()


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: int):
    session = get_session()
    try:
        conversation = conversations.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(404, f"Unknown conversation: {conversation_id}")
        messages = conversations.get_visible_messages(session, conversation_id)
        return {
            **_conversation_dict(conversation),
            "messages": [_message_dict(m) for m in messages],
        }
    finally:
        session.close()


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: int):
    session = get_session()
    try:
        deleted = conversations.delete_conversation(session, conversation_id)
        if not deleted:
            raise HTTPException(404, f"Unknown conversation: {conversation_id}")
        return {"deleted": conversation_id}
    finally:
        session.close()


@app.get("/conversations/{conversation_id}/logs")
async def get_logs(conversation_id: int):
    session = get_session()
    try:
        conversation = conversations.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(404, f"Unknown conversation: {conversation_id}")
        tool_calls = conversations.get_tool_calls(session, conversation_id)
        return [
            {
                "tool_name": tc.tool_name,
                "arguments": tc.arguments_json,
                "status": tc.status,
                "result": tc.result_json,
                "error": tc.error,
                "attempts": tc.attempts,
                "requires_approval": tc.requires_approval,
            }
            for tc in tool_calls
        ]
    finally:
        session.close()


def _send_message_sync(conversation_id: int, content: str) -> dict:
    session = get_session()
    try:
        conversation = conversations.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(404, f"Unknown conversation: {conversation_id}")
        try:
            return agent.send_message(session, conversation, content)
        except ValueError as e:
            raise HTTPException(409, str(e))
    finally:
        session.close()


def _resolve_approval_sync(conversation_id: int, approve: bool) -> dict:
    session = get_session()
    try:
        conversation = conversations.get_conversation(session, conversation_id)
        if conversation is None:
            raise HTTPException(404, f"Unknown conversation: {conversation_id}")
        try:
            return agent.resolve_approval(session, conversation, approve)
        except ValueError as e:
            raise HTTPException(409, str(e))
    finally:
        session.close()


@app.post("/conversations/{conversation_id}/messages")
async def send_message(conversation_id: int, request: MessageRequest):
    # Runs in a thread pool: the agent loop makes blocking OpenAI/DB/tool calls
    # (Playwright, requests, sqlite3) that would otherwise stall the event loop.
    return await asyncio.to_thread(_send_message_sync, conversation_id, request.content)


@app.post("/conversations/{conversation_id}/approve")
async def approve_tool_call(conversation_id: int, request: ApprovalRequest):
    return await asyncio.to_thread(_resolve_approval_sync, conversation_id, request.approve)


@app.get("/health")
async def health():
    return {"status": "ok"}
