from datetime import date,datetime
from pydantic import BaseModel,ConfigDict,Field

class CaseCreateRequest(BaseModel):

    title: str = Field(
        ...,
        min_length = 1,
        max_length=255,
        description="Title or caption of the legal case"
    )

    case_number: str | None = Field(
        default=None,
        max_length=100,
        description="Formal case number or CNR number",
    )

    court_name: str | None = Field(
        default=None,
        max_length=255,
        description="Court or forum name",
    )

    case_type: str | None = Field(
        default=None,
        max_length=100,
        description="Category or type of case",
    )

    status: str = Field(
        default="open",
        max_length=50,
        description="Status of the case (e.g., open, pending, closed)",
    )

    client_name: str | None = Field(
        default=None,
        max_length=255,
        description="Name of the client represented",
    )

    opponent_name: str | None = Field(
        default=None,
        max_length=255,
        description="Name of the opponent or opposing party",
    )

    description: str | None = Field(
        default=None,
        description="Brief background or facts of the case",
    )

    hearing_date: date | None = Field(
        default=None,
        description="Upcoming hearing date",
    )

class CaseUpdateRequest(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated title or caption",
    )
    case_number: str | None = Field(
        default=None,
        max_length=100,
        description="Updated case or CNR number",
    )
    court_name: str | None = Field(
        default=None,
        max_length=255,
        description="Updated court or forum name",
    )
    case_type: str | None = Field(
        default=None,
        max_length=100,
        description="Updated category or type of case",
    )
    status: str | None = Field(
        default=None,
        max_length=50,
        description="Updated case status (e.g. open, pending, closed)",
    )
    client_name: str | None = Field(
        default=None,
        max_length=255,
        description="Updated client name",
    )
    opponent_name: str | None = Field(
        default=None,
        max_length=255,
        description="Updated opposing party name",
    )
    description: str | None = Field(
        default=None,
        description="Updated background or facts",
    )
    hearing_date: date | None = Field(
        default=None,
        description="Updated upcoming hearing date",
    )

class CaseResponse(BaseModel):

    id: int
    user_id: int
    title: str
    case_number: str | None = None
    court_name: str | None = None
    case_type: str | None = None
    status: str
    client_name: str | None = None
    opponent_name: str | None = None
    description: str | None = None
    hearing_date: date | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CaseListResponse(BaseModel):
    items: list[CaseResponse]
    total: int = Field(..., ge=0, description="Total number of matching cases")
    page: int = Field(..., ge=1, description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, description="Number of items per page")


class CaseQARequest(BaseModel):
    query: str = Field(..., min_length=3, description="Legal question or counter-inquiry")
    candidate_pool_size: int = Field(default=20, ge=5, le=50)
    top_k: int = Field(default=5, ge=1, le=10)
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)


class CaseSourceChunk(BaseModel):
    source_type: str | None = None
    document_title: str
    page_number: int
    score: float | None = None


class CaseQAResponse(BaseModel):
    case_id: int
    query: str
    answer: str
    sources: list[CaseSourceChunk]
    grounded: bool
   