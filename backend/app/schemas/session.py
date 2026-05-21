from datetime import datetime

from pydantic import BaseModel, HttpUrl


class SessionBase(BaseModel):
    name: str
    module: str | None = None
    drive_link: HttpUrl
    speaker_name: str | None = None
    speaker_title: str | None = None
    speaker_image_url: HttpUrl | None = None
    intro_video_url: HttpUrl | None = None
    background_image_url: HttpUrl | None = None


class SessionCreate(SessionBase):
    project_id: int


class Session(SessionBase):
    id: int
    project_id: int
    user_id: str
    job_status: str
    created_at: datetime
    updated_at: datetime
