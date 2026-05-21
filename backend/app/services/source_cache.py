"""Cache the original source video in Supabase Storage so the worker
doesn't pull from Google Drive on every per-snippet render.

Layout: `sources/<session_id>.mp4` inside the bucket. The session row
already has a `source_video_stored` boolean — flipping it true on first
successful mirror is what gates subsequent `materialise` calls into the
"download from storage" branch.

We hand back a local path under `workdir`, downloaded via the public
storage URL. The bucket is public-read (see migration 02), so no token
plumbing is needed.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from app.db.supabase import get_supabase_admin
from app.services import fetch, storage


def _source_path(session_id: int) -> str:
    return f"sources/{session_id}.mp4"


def materialise_source(
    session_id: int,
    drive_link: str,
    workdir: Path,
    *,
    google_access_token: str | None = None,
) -> Path:
    """Return a local copy of the session's source video under `workdir`.

    Path used:
      - Already mirrored (`session.source_video_stored = true`) →
        stream from the bucket's public URL into `workdir/source.mp4`.
      - Otherwise → fetch from Drive into `workdir/source.mp4`, upload
        to `sources/<session_id>.mp4`, flip the boolean.
    """
    local = workdir / "source.mp4"
    client = get_supabase_admin()

    row = (
        client.table("session")
        .select("source_video_stored")
        .eq("id", session_id)
        .limit(1)
        .execute()
        .data
    )
    if row and row[0].get("source_video_stored"):
        bucket_url = storage.public_url(_source_path(session_id))
        if bucket_url and _download_from_bucket(bucket_url, local):
            return local
        # Stale flag: bucket has no object. Fall through to re-mirror.

    fetch.fetch_to_disk(
        drive_link, local, google_access_token=google_access_token
    )
    try:
        storage.upload_file(_source_path(session_id), str(local), content_type="video/mp4")
        client.table("session").update({"source_video_stored": True}).eq(
            "id", session_id
        ).execute()
    except Exception:
        # If the mirror upload fails we still have the local copy for
        # this render — leave the flag false so the next render reruns
        # the mirror attempt.
        pass
    return local


def _download_from_bucket(bucket_url: str, dest: Path) -> bool:
    try:
        timeout = httpx.Timeout(connect=30, read=300, write=300, pool=None)
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            with client.stream("GET", bucket_url) as response:
                response.raise_for_status()
                with open(dest, "wb") as fh:
                    for chunk in response.iter_bytes():
                        fh.write(chunk)
    except Exception:
        return False
    return dest.exists() and dest.stat().st_size > 0
