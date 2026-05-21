from datetime import datetime

from pydantic import BaseModel, Field


class SnippetBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    summary: str | None = None
    start_second: int = Field(ge=0)
    end_second: int = Field(ge=0)


class SnippetCreate(SnippetBase):
    session_id: int


class SnippetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    summary: str | None = None
    start_second: int | None = Field(default=None, ge=0)
    end_second: int | None = Field(default=None, ge=0)


class Snippet(SnippetBase):
    id: int
    session_id: int
    intro_id: int | None
    style_name: str | None
    storage_link: str | None
    is_persisted: bool
    created_at: datetime
