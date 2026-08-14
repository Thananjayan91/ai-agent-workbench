import json
from datetime import datetime, timezone

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import Conversation, Message, ToolCall
from backend.tools.registry import requires_approval, run_tool, tool_schemas

_client = OpenAI(api_key=settings.openai_api_key)

_UNRESOLVED_STATUSES = ("pending", "pending_approval", "deferred")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _load_openai_messages(session: Session, conversation_id: int) -> list[dict]:
    rows = session.scalars(
        select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
    )
    openai_messages = []
    for m in rows:
        if m.role == "assistant" and m.tool_calls_json:
            tool_calls = json.loads(m.tool_calls_json)
            openai_messages.append(
                {
                    "role": "assistant",
                    "content": m.content,
                    "tool_calls": [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in tool_calls
                    ],
                }
            )
        elif m.role == "tool":
            openai_messages.append(
                {"role": "tool", "tool_call_id": m.tool_call_id, "content": m.content}
            )
        else:
            openai_messages.append({"role": m.role, "content": m.content})
    return openai_messages


def _execute_with_retry(tool_name: str, arguments: dict) -> tuple[dict | None, str | None, int]:
    attempts = 0
    last_error = None
    while attempts <= settings.tool_max_retries:
        attempts += 1
        try:
            return run_tool(tool_name, arguments), None, attempts
        except Exception as e:  # tool failures shouldn't crash the agent loop
            last_error = str(e)
    return None, last_error, attempts


def _run_tool_and_record(tool_call: ToolCall) -> Message:
    arguments = json.loads(tool_call.arguments_json)
    result, error, attempts = _execute_with_retry(tool_call.tool_name, arguments)
    tool_call.attempts = attempts
    tool_call.resolved_at = _now()
    if error is None:
        tool_call.status = "success"
        tool_call.result_json = json.dumps(result)
        content = json.dumps(result)
    else:
        tool_call.status = "error"
        tool_call.error = error
        content = json.dumps({"error": error})
    return Message(
        conversation_id=tool_call.conversation_id,
        role="tool",
        tool_call_id=tool_call.tool_call_id,
        content=content,
    )


def _tool_call_dict(tc: ToolCall) -> dict:
    return {
        "id": tc.id,
        "tool_call_id": tc.tool_call_id,
        "tool_name": tc.tool_name,
        "arguments": json.loads(tc.arguments_json),
        "status": tc.status,
    }


def _next_unresolved_tool_call(session: Session, conversation_id: int) -> ToolCall | None:
    return session.scalars(
        select(ToolCall)
        .where(
            ToolCall.conversation_id == conversation_id,
            ToolCall.status.in_(_UNRESOLVED_STATUSES),
        )
        .order_by(ToolCall.id)
    ).first()


def _run_loop(session: Session, conversation: Conversation) -> dict:
    model_calls = 0

    while True:
        pending = _next_unresolved_tool_call(session, conversation.id)
        if pending is not None:
            if pending.status == "pending_approval" or (
                pending.status == "deferred" and pending.requires_approval
            ):
                pending.status = "pending_approval"
                conversation.status = "awaiting_approval"
                session.commit()
                return {"status": "awaiting_approval", "tool_call": _tool_call_dict(pending)}

            tool_message = _run_tool_and_record(pending)
            session.add(tool_message)
            session.commit()
            continue

        if model_calls >= settings.max_agent_iterations:
            conversation.status = "active"
            session.commit()
            return {"status": "max_iterations_reached"}

        model_calls += 1
        response = _client.chat.completions.create(
            model=settings.chat_model,
            messages=_load_openai_messages(session, conversation.id),
            tools=tool_schemas(),
            tool_choice="auto",
        )
        choice = response.choices[0].message

        if not choice.tool_calls:
            session.add(
                Message(conversation_id=conversation.id, role="assistant", content=choice.content)
            )
            conversation.status = "active"
            session.commit()
            return {"status": "done", "answer": choice.content}

        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=choice.content,
            tool_calls_json=json.dumps(
                [
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": json.loads(tc.function.arguments),
                    }
                    for tc in choice.tool_calls
                ]
            ),
        )
        session.add(assistant_message)
        session.flush()

        approval_seen = False
        for tc in choice.tool_calls:
            needs_approval = requires_approval(tc.function.name)
            if needs_approval and not approval_seen:
                status = "pending_approval"
            elif approval_seen:
                status = "deferred"
            else:
                status = "pending"
            if needs_approval:
                approval_seen = True

            session.add(
                ToolCall(
                    conversation_id=conversation.id,
                    message_id=assistant_message.id,
                    tool_call_id=tc.id,
                    tool_name=tc.function.name,
                    arguments_json=tc.function.arguments,
                    requires_approval=needs_approval,
                    status=status,
                )
            )
        session.commit()


def send_message(session: Session, conversation: Conversation, content: str) -> dict:
    if conversation.status == "awaiting_approval":
        raise ValueError("Conversation has a pending approval; resolve it before sending a new message")
    session.add(Message(conversation_id=conversation.id, role="user", content=content))
    session.commit()
    return _run_loop(session, conversation)


def resolve_approval(session: Session, conversation: Conversation, approve: bool) -> dict:
    pending = session.scalars(
        select(ToolCall)
        .where(ToolCall.conversation_id == conversation.id, ToolCall.status == "pending_approval")
        .order_by(ToolCall.id)
    ).first()
    if pending is None:
        raise ValueError("No tool call is awaiting approval")

    if approve:
        tool_message = _run_tool_and_record(pending)
    else:
        pending.status = "rejected"
        pending.resolved_at = _now()
        tool_message = Message(
            conversation_id=conversation.id,
            role="tool",
            tool_call_id=pending.tool_call_id,
            content=json.dumps({"error": "User rejected this action; it was not executed."}),
        )

    session.add(tool_message)
    conversation.status = "active"
    session.commit()
    return _run_loop(session, conversation)
