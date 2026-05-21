"""Download a video referenced by a Google Drive link.

Two paths:

  - **Public link** (default): `gdown` — handles the large-file
    confirmation hop without auth. Works when the source is shared as
    "anyone with the link".

  - **Authenticated** (`download_with_token`): direct call to
    `files/{id}?alt=media` with a `Bearer` OAuth token. Wired for when
    the frontend passes `supabase.auth.getSession().provider_token`
    through the API.

Hardening notes:

  - **Hostname is checked** before the regex extraction: only
    `drive.google.com` and `docs.google.com` are accepted. Without
    this, a URL like `https://evil.example.com/?id=AAA` would still
    match the second `[?&]id=` pattern and be handed to gdown.
  - **`fuzzy=False`** when calling `gdown.download`. We've already
    extracted the file id; fuzzy mode lets gdown follow alternative
    URL shapes (including some that scrape arbitrary HTML), which we
    don't need.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse

import gdown
import httpx

_ALLOWED_HOSTS = ("drive.google.com", "docs.google.com")

_ID_PATTERNS = (
    re.compile(r"/file/d/([A-Za-z0-9_-]+)"),
    re.compile(r"[?&]id=([A-Za-z0-9_-]+)"),
)


def is_drive_url(url: str) -> bool:
    """Stricter than the previous substring check — parses the URL and
    matches the hostname against a fixed allow-list."""
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host in _ALLOWED_HOSTS or any(host.endswith("." + h) for h in _ALLOWED_HOSTS)


def extract_file_id(drive_link: str) -> str:
    if not is_drive_url(drive_link):
        raise ValueError(f"Not a Google Drive URL: {drive_link}")
    for pat in _ID_PATTERNS:
        m = pat.search(drive_link)
        if m:
            return m.group(1)
    raise ValueError(f"Could not extract a Drive file id from: {drive_link}")


def download(drive_link: str, dest_path: str | Path) -> Path:
    """Public-link download via gdown."""
    file_id = extract_file_id(drive_link)
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    gdown.download(id=file_id, output=str(out), quiet=True, fuzzy=False)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(
            f"Public Drive download produced no file: id={file_id}. "
            "Confirm the file is shared as 'Anyone with the link'."
        )
    return out


def download_with_token(
    drive_link: str, access_token: str, dest_path: str | Path
) -> Path:
    """Authenticated download via Drive API v3.

    `access_token` is the user's Google OAuth access token (the
    `provider_token` Supabase surfaces after a `signInWithOAuth({
    provider: 'google' })` round-trip). Tokens expire — refresh on the
    frontend or pass a fresh one each call.
    """
    file_id = extract_file_id(drive_link)
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}"
    timeout = httpx.Timeout(connect=30, read=300, write=300, pool=None)
    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        with client.stream(
            "GET",
            url,
            params={"alt": "media", "supportsAllDrives": "true"},
            headers={"Authorization": f"Bearer {access_token}"},
        ) as response:
            response.raise_for_status()
            with open(out, "wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)

    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(
            f"Authenticated Drive download produced no file: id={file_id}"
        )
    return out
