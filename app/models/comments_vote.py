from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Boolean, ForeignKey, UniqueConstraint

from app.database import Base


class CommentVoteModel(Base):
    __tablename__ = "comments_votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    comment_id: Mapped[int] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False
    )

    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "comment_id", name="uq_user_decision_comment_vote"),
    )

    # relationships
    user: Mapped["UserModel"] = relationship(back_populates="comment_votes")
    comment: Mapped["CommentModel"] = relationship(back_populates="comment_votes")