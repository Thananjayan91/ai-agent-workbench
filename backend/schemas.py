from pydantic import BaseModel


class ConversationCreateRequest(BaseModel):
    title: str = "New conversation"


class MessageRequest(BaseModel):
    content: str


class ApprovalRequest(BaseModel):
    approve: bool
