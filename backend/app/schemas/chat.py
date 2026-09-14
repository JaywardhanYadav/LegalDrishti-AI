from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreateRequest(BaseModel):
    title: str = Field(default="New Chat", max_length=255)
    case_id: int | None = None


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    case_id: int | None = None
    title: str
    created_at: datetime
    updated_at: datetime
    messages_count: int = 0


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionResponse]
    total: int


class ChatMessageCreateRequest(BaseModel):
    query: str | None = None
    content: str | None = None
    mode: str = "dual_stream"  # "dual_stream" or "deep_search"
    case_id: int | None = None

    def get_query(self) -> str:
        return (self.query or self.content or "").strip()


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    sources: list[str] = []
    token_count: int = 0
    created_at: datetime


class ChatSessionDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    file_name: str
    file_size_bytes: int
    created_at: datetime


class ChatTranscriptResponse(BaseModel):
    session_id: int
    title: str
    case_id: int | None = None
    messages: list[ChatMessageResponse]
    documents: list[ChatSessionDocumentResponse] = []
