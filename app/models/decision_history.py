from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Integer, String, Boolean, DateTime, ForeignKey, Index, func, TEXT
)
from datetime import datetime
from app.database import Base
from typing import Optional


class DecisionHistoryModel(Base):
    __tablename__ = "decision_history"
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(TEXT, nullable=True)
    image_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    decision_id : Mapped[int] = mapped_column(ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True,  nullable=False)

    decision : Mapped["DecisionModel"] = relationship(back_populates="decision_history")