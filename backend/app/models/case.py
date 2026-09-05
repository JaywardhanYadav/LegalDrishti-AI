from datetime import date, datetime
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Case(Base):

    __tablename__ = "cases"

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

    case_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    
    court_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    case_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    
    status: Mapped[str] = mapped_column(
        String(50),
        default="open",
        nullable=False,
    )
    
    client_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    opponent_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
  
    hearing_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
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
        """
        return f"<Case(id={self.id}, user_id={self.user_id}, title='{self.title}', status='{self.status}')>"
