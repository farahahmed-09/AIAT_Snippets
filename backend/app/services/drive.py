"""Download a video referenced by a Google Drive link.

Two paths:

  - **Public link** (default): `gdown` — handles the large-file
    confirmation hop without auth. Works when the source is shared as
    "anyone with the link".

  - **Authenticated** (`download_with_token`): direct call to
    `files/{id}?alt=media` with a `Bearer` OAuth token. Plug this in
    when the caller (a user who signed in via Google) is willing to
    surface their `provider_token` to the backend — e.g., the frontend
    passes `supabase.auth.getSession().provider_token` on the
    create-session request and we forward it to the worker.

The split keeps the simple case simple while leaving an easy upgrade
path for private files.
"""

from __future__ import annotations

import re
from pathlib import Path

import gdown
import httpx


_ID_PATTERNS = (
    re.compile(r"/file/d/([A-Za-z0-9_-]+)"),
    re.compile(r"[?&]id=([A-Za-z0-9_-]+)"),
)


def extract_file_id(drive_link: str) -> str:
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
    gdown.download(id=file_id, output=str(out), quiet=True, fuzzy=True)
    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"Public Drive download produced no file: id={file_id}")
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
    with httpx.Client(timeout=300, follow_redirects=True) as client:
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
        raise RuntimeError(f"Authenticated Drive download produced no file: id={file_id}")
    return out
