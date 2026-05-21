from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

JobStatus = Literal["Pending", "Processing", "Finished", "Failed"]


class SessionBranding(BaseModel):
    speaker_name: str | None = None
    speaker_title: str | None = None
    speaker_image_url: HttpUrl | None = None
    intro_video_url: HttpUrl | None = None
    background_image_url: HttpUrl | None = None


class SessionCreate(SessionBranding):
    name: str = Field(min_length=1, max_length=200)
    module: str | None = None
    drive_link: HttpUrl


class SessionUpdate(SessionBranding):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    module: str | None = None


class Session(SessionBranding):
    id: int
    project_id: int
    user_id: str
    name: str
    module: str | None
    drive_link: HttpUrl
    job_status: str
    source_video_stored: bool
    created_at: datetime
    started_at: datetime | None
    updated_at: datetime
    completed_at: datetime | None
    last_accessed_at: datetime | None
