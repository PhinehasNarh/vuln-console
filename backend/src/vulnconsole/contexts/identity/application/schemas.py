"""Identity request/response models."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"  # noqa: S105 (OAuth2 token type, not a credential)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    role: str
    is_active: bool
    created_at: datetime


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9._-]+$")
    password: str = Field(min_length=12, max_length=128)
    role: str


class CreateApiTokenRequest(BaseModel):
    name: str = Field(min_length=3, max_length=120)


class ApiTokenCreatedOut(BaseModel):
    id: uuid.UUID
    name: str
    token: str  # plaintext, shown exactly once
