from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class CaseDocument(Base):

    __tablename__ = "case_documents"

    __table_args__ = (
        UniqueConstraint("case_id", "document_id", name="uq_case_document"),
    )

    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    
    case_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("cases.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    
    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    exhibit_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    relevance_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    case = relationship("Case", foreign_keys=[case_id])
    document = relationship("Document", foreign_keys=[document_id])
    def __repr__(self) -> str:
        
        return (
            f"<CaseDocument(id={self.id}, case_id={self.case_id}, "
            f"document_id={self.document_id}, exhibit='{self.exhibit_label}')>"
        )