from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from user_note.backend.db.base import Base
from user_note.backend.db.types import UTCDateTime


def _now() -> datetime:
    return datetime.now(UTC)


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    importance: Mapped[str] = mapped_column(
        String(20), nullable=False, default="normal"
    )
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(), nullable=False, default=_now, onupdate=_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    owner = relationship("User", back_populates="notes")

    __table_args__ = (
        Index("ix_notes_owner_deleted", "owner_id", "deleted_at"),
        Index("ix_notes_owner_status", "owner_id", "status"),
        Index("ix_notes_owner_importance", "owner_id", "importance"),
    )
