from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class DocumentResponse(BaseModel):
    id:int
    user_id: int
    title: str
    file_name: str
    file_size_bytes: str
    mime_type: str
    file_hash: str
    document_type:str
    processing_status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class DocumentDetailResponse(DocumentResponse):
    extracted_text: str | None = None

class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    total: int = Field(..., ge=0, description="Total number of matching documents")
    page: int = Field(..., description="Current page number (1-indexed)")
    page_size: int = Field(..., ge=1, description="Number of items per page")

class DocumentUpdateRequest(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated document title"
    )

    document_type: str | None = Field(
        default=None,
        max_length=50,
        description="Category (e.g, Petition, order, evidence, contract, general)"
    )