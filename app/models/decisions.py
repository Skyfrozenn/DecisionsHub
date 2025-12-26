from sqlalchemy import func, Integer, TEXT, Boolean, DateTime, ForeignKey, Computed, String, Index
from sqlalchemy.orm import Mapped,mapped_column, relationship
from sqlalchemy.dialects.postgresql import TSVECTOR
from app.database import Base

from datetime import datetime
from typing import Optional



class DecisionModel(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)                               
    title: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(TEXT, default=None, nullable=True)
    image_url : Mapped[Optional[str]] = mapped_column(String(255), default=None, nullable=True)
    user_id : Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    status : Mapped[str] = mapped_column(default="in_processing", nullable=False)
    is_active : Mapped[bool] = mapped_column(default=True, nullable=False)
    tsv : Mapped[TSVECTOR] = mapped_column(
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
        Index('decisions_tsv_gin', "tsv", postgresql_using='gin'),
        Index('decisions_trgm', "title", postgresql_using='gin', postgresql_ops={'title': 'gin_trgm_ops'})
    )
    user : Mapped["UserModel"] = relationship(back_populates="decisions")
    
     