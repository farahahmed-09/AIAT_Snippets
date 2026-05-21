"""Unified `URL → local file` helper used by the worker.

  - Google Drive link + `google_access_token`  → authenticated Drive API
  - Google Drive link (no token)               → gdown public-link path
  - Everything else                            → streamed httpx GET
"""

from __future__ import annotations

from pathlib import Path

import httpx

from app.services import drive


def fetch_to_disk(
    url: str,
    dest_path: str | Path,
    *,
    google_access_token: str | None = None,
) -> Path:
    out = Path(dest_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if "drive.google.com" in url:
        if google_access_token:
            return drive.download_with_token(url, google_access_token, out)
        return drive.download(url, out)

    with httpx.Client(timeout=300, follow_redirects=True) as client:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(out, "wb") as fh:
                for chunk in response.iter_bytes():
                    fh.write(chunk)

    if not out.exists() or out.stat().st_size == 0:
        raise RuntimeError(f"Download produced no file: {url}")
    return out
