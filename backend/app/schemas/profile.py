from datetime import datetime

from pydantic import BaseModel


class Profile(BaseModel):
    id: str
    email: str | None
    full_name: str | None
    avatar_url: str | None
    created_at: datetime
    updated_at: datetime


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None
