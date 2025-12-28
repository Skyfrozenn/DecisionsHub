from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, Boolean, ForeignKey, UniqueConstraint

from app.database import Base


class DecisionVoteModel(Base):
    __tablename__ = "decision_votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    decision_id: Mapped[int] = mapped_column(
        ForeignKey("decisions.id", ondelete="CASCADE"),
        nullable=False
    )

    is_like: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "decision_id", name="uq_user_decision_vote"),
    )

    # relationships
    user: Mapped["UserModel"] = relationship(back_populates="votes")
    decision: Mapped["DecisionModel"] = relationship(back_populates="votes")
