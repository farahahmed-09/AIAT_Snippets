
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# --- Snippet Schemas ---


class SnippetBase(BaseModel):
    name: str
    summary: Optional[str] = None
    start_second: int
    end_second: int
    intro_id: Optional[int] = None
    style_name: Optional[str] = None
    intro_metadata: Optional[str] = None


class SnippetCreate(SnippetBase):
    pass


class SnippetResponse(SnippetBase):
    id: int
    session_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# --- Session Schemas ---


# class SessionBase(BaseModel):
#     name: str
#     module: Optional[str] = None
#     drive_link: Optional[str] = None
#     video_url: Optional[str] = None

class SessionBase(BaseModel):
    name: str
    module: Optional[str] = None
    drive_link: Optional[str] = None
    video_url: Optional[str] = None

    # --- FIX STARTS HERE ---
    # Rename these to match the frontend JSON keys exactly
    speaker_name: Optional[str] = None
    speaker_title: Optional[str] = None
    # Changed from speaker_image_base64
    speaker_image_url: Optional[str] = None
    # Changed from intro_video_base64
    intro_video_url: Optional[str] = None
    # Changed from background_image_base64
    background_image_url: Optional[str] = None
    # --- FIX ENDS HERE ---


class SessionCreate(SessionBase):
    pass


class SessionUpdate(BaseModel):
    job_status: Optional[str] = None
    completed_at: Optional[datetime] = None


class SessionResponse(SessionBase):
    id: int
    created_at: datetime
    started_at: Optional[datetime] = None
    updated_at: datetime
    completed_at: Optional[datetime] = None
    job_status: str
    video_url: Optional[str] = None
    snippets: List[SnippetResponse] = []

    class Config:
        from_attributes = True

# --- Job/Plan Update Schemas ---


class PlanUpdateItem(BaseModel):
    name: Optional[str] = None
    start: Optional[float] = None  # mapping from 'start' in JSON
    end: Optional[float] = None
    summary: Optional[str] = None


class PlanUpdate(BaseModel):
    snippets: List[PlanUpdateItem]


class IntroUpload(BaseModel):
    name: str
    video_base64: str
    thumbnail_base64: str
