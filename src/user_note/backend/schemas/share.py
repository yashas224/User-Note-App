from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from user_note.backend.schemas.note import Importance, Status


class ShareCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # None means the link never expires.
    expires_in_days: int | None = Field(7, ge=1, le=365)


class ShareCreated(BaseModel):
    id: int
    share_url: str
    expires_at: datetime | None


class ShareRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    is_active: bool


class SharedNote(BaseModel):
    """Public view: only approved fields, no IDs or owner info."""

    model_config = ConfigDict(from_attributes=True)

    title: str
    body: str
    status: Status
    importance: Importance
    updated_at: datetime
