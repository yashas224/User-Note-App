from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Status(StrEnum):
    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"


class Importance(StrEnum):
    low = "low"
    normal = "normal"
    high = "high"
    critical = "critical"


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    status: Status = Status.draft
    body: str = ""
    importance: Importance = Importance.normal


class NoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    status: Status
    body: str
    importance: Importance
    created_at: datetime
    updated_at: datetime
