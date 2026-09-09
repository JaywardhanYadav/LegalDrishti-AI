from pydantic import BaseModel, Field


class LegalResearchRequest(BaseModel):
    query: str = Field(
        ...,
        min_length=5,
        description="Legal issue, statute section, or proposition to research",
    )
    court_filter: str | None = Field(
        default=None,
        description="Optional filter: 'Supreme Court', 'Delhi High Court', 'Bombay High Court', etc.",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of authoritative precedents to retrieve",
    )


class PrecedentItem(BaseModel):
    case_title: str
    citation: str | None = None
    court: str
    year: str | None = None
    ratio_decidendi: str
    source_url: str


class LegalResearchResponse(BaseModel):
    query: str
    synthesis: str
    precedents: list[PrecedentItem]
    total_found: int
    remaining_credits: int
