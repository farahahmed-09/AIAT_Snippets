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


def make_snippet_path(session_id: int, snippet_id: int) -> str:
    """Where a rendered snippet artifact lives in the bucket.

    Versioned with a uuid suffix so re-renders never overwrite (a viewer
    holding the old URL keeps streaming the old cut while the new one
    publishes). Whatever's no longer linked from a row can be garbage-
    collected by a background job later.
    """
    return f"snippets/{session_id}/{snippet_id}_{uuid.uuid4().hex}.mp4"


def upload_file(path: str, source: str | bytes, *, content_type: str | None = None) -> str:
    """Upload from a local path (preferred for big artifacts) and return
    the bucket key. Falls back to bytes if `source` is bytes."""
    if isinstance(source, bytes):
        return upload_bytes(path, source, content_type=content_type)
    with open(source, "rb") as f:
        data = f.read()
    return upload_bytes(path, data, content_type=content_type or "video/mp4")


def _default_suffix(kind: str) -> str:
    return ".mp4" if kind == "video" else ".jpg"


def guess_content_type(filename: str, fallback: str) -> str:
    return mimetypes.guess_type(filename)[0] or fallback
