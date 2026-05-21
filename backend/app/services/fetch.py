"""Unified `URL → local file` helper used by the worker.

  - Drive URL (hostname matches `drive.google.com` / `docs.google.com`)
    + `google_access_token`  → authenticated Drive API
  - Drive URL without a token                       → gdown public path
  - Everything else                                 → streamed httpx GET
    (CAUTION: only invoked for URLs we control — intro_video_url and
    speaker_image_url originate from our own Supabase Storage bucket,
    so SSRF surface is limited to that allow-list. If we ever accept
    arbitrary user URLs here, add a hostname allow-list — see the
    `_ALLOWED_PASSTHROUGH_HOSTS` constant for the seam.)
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.services import drive
from app.core.config import get_settings


def fetch_to_disk(
    url: str,
    dest_path: str | Path,
    *,
    google_access_token: str | None = None,
) -> Path:
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if drive.is_drive_url(url):
        if google_access_token:
            return drive.download_with_token(url, google_access_token, out)
        return drive.download(url, out)

    _assert_passthrough_allowed(url)

    timeout = httpx.Timeout(connect=30, read=300, write=300, pool=None)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(out, "wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)

    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"Download produced no file: {url}")
    return out


def _assert_passthrough_allowed(url: str) -> None:
    """Allow only the configured Supabase project host. Closes the SSRF
    door for `intro_video_url` / `speaker_image_url` (those URLs always
    come from our own Storage bucket in normal flow)."""
    settings = get_settings()
    host = (urlparse(url).hostname or "").lower()
    supabase_host = (urlparse(settings.supabase_url).hostname or "").lower()
    if host != supabase_host:
        raise RuntimeError(
            f"Refusing to fetch non-Drive, non-Supabase URL: {url}"
        )
