from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
class DraftTypeEnum(str, Enum):
    NOTICE_138_NI_ACT = "notice_138_ni_act"
    ANTICIPATORY_BAIL_BNSS = "anticipatory_bail_bnss"
    LEGAL_AFFIDAVIT = "legal_affidavit"
    REPLY_LEGAL_NOTICE = "reply_legal_notice"
class DraftGenerateRequest(BaseModel):
    draft_type: DraftTypeEnum = Field(
        description="Type of legal document: notice_138_ni_act, anticipatory_bail_bnss, legal_affidavit, reply_legal_notice",
    )
    case_id: int | None = Field(
        default=None,
        description="Optional case ID to auto-populate facts from case files",
    )
    title: str | None = Field(
        default=None,
        max_length=255,
        description="Custom title for this draft",
    )
    court_name: str | None = Field(
        default=None,
        max_length=255,
        description="Target court (e.g. 'In the Court of Judicial Magistrate First Class, Pune')",
    )
    jurisdiction: str = Field(
        default="India",
        max_length=100,
        description="State or city jurisdiction",
    )
    custom_facts: str | None = Field(
        default=None,
        description="Specific dates, cheque details, party names, or transaction facts provided by the advocate",
    )
    special_instructions: str | None = Field(
        default=None,
        description="Any specific prayer, urgency grounds, or statutory relief to include",
    )
class DraftUpdateRequest(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    content: str | None = Field(default=None, description="Updated draft body")
    court_name: str | None = Field(default=None, max_length=255)
    jurisdiction: str | None = Field(default=None, max_length=100)
class ValidationItem(BaseModel):
    rule_name: str
    passed: bool
    details: str
class DraftResponse(BaseModel):
    id: int
    user_id: int
    case_id: int | None = None
    title: str
    draft_type: str
    content: str
    jurisdiction: str
    court_name: str | None = None
    validation_status: str
    validation_report: str | None = None
    version: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
class DraftListResponse(BaseModel):
    items: list[DraftResponse]
    total: int
    page: int
    page_size: int
