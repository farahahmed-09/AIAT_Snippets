from datetime import datetime

from pydantic import BaseModel


class SnippetBase(BaseModel):
    name: str
    summary: str | None = None
    start_second: int
    end_second: int


class SnippetCreate(SnippetBase):
    session_id: int


class Snippet(SnippetBase):
    id: int
    session_id: int
    storage_link: str | None = None
    is_persisted: bool = False
    created_at: datetime
