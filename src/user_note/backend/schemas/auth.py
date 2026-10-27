from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from user_note.backend.core.config import settings


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    password: str = Field(max_length=128)

    @field_validator("password")
    @classmethod
    def _min_length(cls, v: str) -> str:
        if len(v) < settings.PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters"
            )
        return v


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime
