from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
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
    
    case_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("cases.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    
    title: Mapped[str] = mapped_column(
        String(255),
        default="New Legal Chat",
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
    case = relationship("Case", foreign_keys=[case_id])
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    def __repr__(self) -> str:
        
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, title='{self.title}')>"


class ChatMessage(Base):
    
    __tablename__ = "chat_messages"
    
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        index=True,
    )

    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    
    sources: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    
    session = relationship("ChatSession", back_populates="messages")
    def __repr__(self) -> str:
        
        return f"<ChatMessage(id={self.id}, session_id={self.session_id}, role='{self.role}')>"