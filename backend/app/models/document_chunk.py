from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
   
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk_index"),
    )
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    
    section_heading: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    vector_id: Mapped[str | None] = mapped_column(
        String(100),
        index=True,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    document = relationship("Document", foreign_keys=[document_id])
    def __repr__(self) -> str:
    
        return (
            f"<DocumentChunk(id={self.id}, document_id={self.document_id}, "
            f"index={self.chunk_index}, page={self.page_number})>"
        )