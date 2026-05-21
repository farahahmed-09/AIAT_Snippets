"""End-to-end pipeline orchestration.

Stages:
  1. Download the source video referenced by `drive_link`.
  2. Transcribe it (chunked, via ai_core `audio.transcribe_segments`).
  3. Propose snippet boundaries (ai_core `snippets.segment_transcript`
     + `snippets.cleanse_segments`).
  4. Insert one snippet row per proposal — status becomes 'Finished'.
  5. Per-snippet render runs on demand from the UI.

The Celery worker calls `run_session_pipeline(session_id)`. Each step
updates `session.job_status` so the polling UI shows progress. All
artifacts are transient (held under a TemporaryDirectory); only DB
rows persist between stages.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.db.supabase import get_supabase_admin
from app.services import fetch, segment, transcribe


def set_status(session_id: int, status: str) -> None:
    client = get_supabase_admin()
    client.table("session").update({"job_status": status}).eq(
        "id", session_id
    ).execute()


def fail(session_id: int, message: str) -> None:
    set_status(session_id, f"Failed: {message}")


def run_session_pipeline(session_id: int) -> None:
    client = get_supabase_admin()
    rows = (
        client.table("session")
        .select("*")
        .eq("id", session_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        return
    session = rows[0]

    with tempfile.TemporaryDirectory(prefix=f"session-{session_id}-") as tmp:
        workdir = Path(tmp)
        try:
            set_status(session_id, "Processing: downloading")
            source_path = workdir / "source.mp4"
            fetch.fetch_to_disk(session["drive_link"], source_path)

            set_status(session_id, "Processing: transcribing")
            transcript = transcribe.transcribe(str(source_path))

            set_status(session_id, "Processing: segmenting")
            proposals = segment.segment(transcript)

            set_status(session_id, "Processing: persisting")
            client.table("snippet").delete().eq("session_id", session_id).execute()
            if proposals:
                client.table("snippet").insert(
                    [
                        {
                            "session_id": session_id,
                            "name": p.name,
                            "summary": p.summary,
                            "start_second": p.start_second,
                            "end_second": p.end_second,
                        }
                        for p in proposals
                    ]
                ).execute()

            set_status(session_id, "Finished")
        except NotImplementedError as exc:
            fail(session_id, str(exc))
        except Exception as exc:  # noqa: BLE001 — surface anything to the UI
            fail(session_id, f"unhandled error: {exc!s}")
