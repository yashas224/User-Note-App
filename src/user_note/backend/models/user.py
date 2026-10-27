from datetime import UTC, datetime

from sqlalchemy import Boolean, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from user_note.backend.db.base import Base
from user_note.backend.db.types import UTCDateTime


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=lambda: datetime.now(UTC)
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    notes = relationship("Note", back_populates="owner")

    __table_args__ = (
        Index("ix_users_username_lower", func.lower(username), unique=True),
    )
