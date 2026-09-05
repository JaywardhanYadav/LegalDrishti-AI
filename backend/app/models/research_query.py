from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class ResearchQuery(Base):
   
    __tablename__ = "research_queries"

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

    query_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    
    jurisdiction: Mapped[str] = mapped_column(
        String(100),
        default="India",
        nullable=False,
    )

    
    search_provider: Mapped[str] = mapped_column(
        String(50),
        default="tavily",
        nullable=False,
    )

    
    retrieved_sources: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )


    synthesized_response: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    
    status: Mapped[str] = mapped_column(
        String(50),
        default="completed",
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

    def __repr__(self) -> str:
        
        return (
            f"<ResearchQuery(id={self.id}, user_id={self.user_id}, "
            f"jurisdiction='{self.jurisdiction}', status='{self.status}')>"
        )
