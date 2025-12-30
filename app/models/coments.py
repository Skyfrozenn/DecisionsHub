from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Boolean, ForeignKey, UniqueConstraint, TEXT, DateTime,func

from app.database import Base

from datetime import datetime
from typing import Optional


class CommentModel(Base):
    __tablename__ = "comments"

    __table_args__ = (
        UniqueConstraint("user_id", "decision_id", name="uq_user_decision_comment"),
    )
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    text : Mapped[str] = mapped_column(TEXT,nullable=False)
    decision_id : Mapped[int] = mapped_column(Integer, ForeignKey("decisions.id",ondelete="CASCADE"), nullable=False)
    user_id : Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    parent_id : Mapped[int | None] = mapped_column(ForeignKey("comments.id"), nullable=True)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    status : Mapped[bool] = mapped_column(default=True, nullable=False)

    children : Mapped[list["CommentModel"]] = relationship(back_populates="parent")  
    parent : Mapped[Optional["CommentModel"]] = relationship(back_populates="children", remote_side="CommentModel.id")

    user: Mapped["UserModel"] = relationship(back_populates="comments")
    decision: Mapped["DecisionModel"] = relationship(back_populates="comments")
    comment_votes : Mapped[list["CommentVoteModel"]] =  relationship(
        back_populates="comment",
        cascade="all, delete-orphan"
    )

 

