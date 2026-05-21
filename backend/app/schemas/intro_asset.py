from datetime import datetime

from pydantic import BaseModel


class IntroAsset(BaseModel):
    id: int
    project_id: int
    name: str
    video_url: str
    thumbnail_url: str | None
    created_by: str | None
    created_at: datetime
