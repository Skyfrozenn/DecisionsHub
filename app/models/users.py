from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Boolean, DateTime, func

from datetime import datetime

from app.database import Base




class UserModel(Base):
    __tablename__ = "users"
    id : Mapped[int] = mapped_column(Integer, primary_key=True)
    name : Mapped[str] = mapped_column(String(20), nullable=False)
    email : Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    password : Mapped[str] = mapped_column(String(255), nullable=False)
    role : Mapped[str] = mapped_column(String(15), default="admin")
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_active : Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


