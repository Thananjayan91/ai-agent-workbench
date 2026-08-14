from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models import Conversation, Message, ToolCall

SYSTEM_PROMPT = (
    "You are a tool-using agent. Use the available tools to find real information, "
    "perform calculations, and save reports rather than guessing or making up numbers. "
    "The save_report tool writes to disk and requires human approval before it runs, "
    "so only call it once you have everything needed to finalize a report."
)


def create_conversation(session: Session, title: str) -> Conversation:
    conversation = Conversation(title=title)
    session.add(conversation)
    session.flush()
    session.add(Message(conversation_id=conversation.id, role="system", content=SYSTEM_PROMPT))
    session.commit()
    session.refresh(conversation)
    return conversation


def list_conversations(session: Session) -> list[Conversation]:
    return list(session.scalars(select(Conversation).order_by(Conversation.id)))


def get_conversation(session: Session, conversation_id: int) -> Conversation | None:
    return session.get(Conversation, conversation_id)


def delete_conversation(session: Session, conversation_id: int) -> bool:
    conversation = session.get(Conversation, conversation_id)
    if conversation is None:
        return False
    session.delete(conversation)
    session.commit()
    return True


def get_visible_messages(session: Session, conversation_id: int) -> list[Message]:
    return list(
        session.scalars(
            select(Message)
            .where(Message.conversation_id == conversation_id, Message.role != "system")
            .order_by(Message.id)
        )
    )


def get_tool_calls(session: Session, conversation_id: int) -> list[ToolCall]:
    return list(
        session.scalars(
            select(ToolCall)
            .where(ToolCall.conversation_id == conversation_id)
            .order_by(ToolCall.id)
        )
    )
