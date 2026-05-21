"""End-to-end pipeline orchestration.

Stages:
  1. Download the source video referenced by `drive_link`.
  2. Transcribe it (services.transcribe).
  3. Ask an LLM to propose snippet boundaries (services.segment).
  4. Insert one snippet row per proposal — status becomes 'Finished'.
  5. Per-snippet render runs on demand from the UI (services.render).

The Celery worker calls `run_session_pipeline(session_id)`. Each step
updates `session.job_status` so the polling UI shows progress.
"""

from __future__ import annotations

from app.db.supabase import get_supabase_admin
from app.services import segment, transcribe


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

    try:
        set_status(session_id, "Processing: downloading")
        # TODO: download via google drive client; write to /tmp
        source_path = _download_source(session["drive_link"])

        set_status(session_id, "Processing: transcribing")
        transcript = transcribe.transcribe(source_path)

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


def _download_source(drive_link: str) -> str:
    """TODO: pull the file via google drive API to /tmp and return path."""
    _ = drive_link
    raise NotImplementedError("Drive download not wired yet.")
