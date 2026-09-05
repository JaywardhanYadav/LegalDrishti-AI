
from datetime import datetime
from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Document(Base):
    
    
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    file_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    
    file_path: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    
    file_size_bytes: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
    )
    
    mime_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    
    file_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    
    document_type: Mapped[str] = mapped_column(
        String(50),
        default="general",
        nullable=False,
    )
    
    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    
    processing_status: Mapped[str] = mapped_column(
        String(50),
        default="uploaded",
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
   
    user = relationship("User", foreign_keys=[user_id])
    def __repr__(self) -> str:
        """
        Safe string representation for debugging.
        Excludes document text content to keep logs clean and private.
        """
        return (
            f"<Document(id={self.id}, user_id={self.user_id}, "
            f"title='{self.title}', status='{self.processing_status}')>"
        )
