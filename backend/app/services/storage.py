from __future__ import annotations

import mimetypes
import uuid
from pathlib import PurePosixPath

from app.core.config import get_settings
from app.db.supabase import get_supabase_admin


def upload_bytes(
    path: str, data: bytes, *, content_type: str | None = None
) -> str:
    """Upload to the configured bucket; returns the storage key."""
    client = get_supabase_admin()
    settings = get_settings()
    client.storage.from_(settings.supabase_bucket).upload(
        path=path,
        file=data,
        file_options={
            "content-type": content_type or "application/octet-stream",
            "upsert": "true",
        },
    )
    return path


def delete_object(path: str) -> None:
    client = get_supabase_admin()
    settings = get_settings()
    client.storage.from_(settings.supabase_bucket).remove([path])


def public_url(path: str | None) -> str | None:
    if not path:
        return None
    client = get_supabase_admin()
    settings = get_settings()
    return client.storage.from_(settings.supabase_bucket).get_public_url(path)


def make_intro_path(project_id: int, filename: str, kind: str) -> str:
    """`kind` is 'video' or 'thumbnail'. Keeps the original extension."""
    suffix = PurePosixPath(filename).suffix or _default_suffix(kind)
    return f"intros/{project_id}/{uuid.uuid4().hex}{kind[0]}{suffix.lower()}"


def _default_suffix(kind: str) -> str:
    return ".mp4" if kind == "video" else ".jpg"


def guess_content_type(filename: str, fallback: str) -> str:
    return mimetypes.guess_type(filename)[0] or fallback
