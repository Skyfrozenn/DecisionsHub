from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Integer, String, Boolean, DateTime, ForeignKey, Index, func, TEXT
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.schema import Computed
from datetime import datetime
from typing import Optional

from app.database import Base


class DecisionModel(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    title: Mapped[str] = mapped_column(String(100),  nullable=False)
    description: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    status: Mapped[str] = mapped_column(
        String(20), default="in_processing", nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )

    tsv: Mapped[TSVECTOR] = mapped_column(
        TSVECTOR,
        Computed(
            """
            setweight(to_tsvector('english', coalesce(title, '')), 'A')
            || setweight(to_tsvector('russian', coalesce(title, '')), 'A')
            || setweight(to_tsvector('english', coalesce(description, '')), 'B')
            || setweight(to_tsvector('russian', coalesce(description, '')), 'B')
            """,
            persisted=True
        ),
        nullable=False
    )

    __table_args__ = (
        Index("decisions_tsv_gin", "tsv", postgresql_using="gin"),
        Index(
            "decisions_trgm",
            "title",
            postgresql_using="gin",
            postgresql_ops={"title": "gin_trgm_ops"}
        ),
    )

    # relationships
    user: Mapped["UserModel"] = relationship(back_populates="decisions")

    votes: Mapped[list["DecisionVoteModel"]] = relationship(
        back_populates="decision",
        cascade="all, delete-orphan",
    )

    decision_history : Mapped[list["DecisionHistoryModel"]] = relationship(
        back_populates="decision",
        cascade="all, delete-orphan",
    )
    
     