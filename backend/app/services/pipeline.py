"""End-to-end pipeline orchestration.

Stages:
  1. Materialise the source video (Supabase Storage cache → fall back to
     Drive download on cache miss, then mirror).
  2. Transcribe it (chunked, via ai_core `audio.transcribe_segments`).
  3. Propose snippet boundaries (ai_core `snippets.segment_transcript`
     + `snippets.cleanse_segments`).
  4. Reconcile: keep persisted snippets (`is_persisted=true`) untouched,
     replace only the draft ones. Avoids destroying any rendered URLs
     when the user re-runs the pipeline.
  5. Per-snippet render runs on demand from the UI.

The Celery worker calls `run_session_pipeline(session_id)`. Each step
updates `session.job_status` so the polling UI shows progress. All
local artifacts are transient (held under a TemporaryDirectory); only
DB rows + storage objects persist between stages.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from app.db.supabase import get_supabase_admin
from app.services import segment, source_cache, transcribe


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

    now_iso = datetime.now(timezone.utc).isoformat()
    client.table("session").update({"started_at": now_iso}).eq(
        "id", session_id
    ).execute()

    with tempfile.TemporaryDirectory(prefix=f"session-{session_id}-") as tmp:
        workdir = Path(tmp)
        try:
            set_status(session_id, "Processing: downloading")
            source_path = source_cache.materialise_source(
                session_id, session["drive_link"], workdir
            )

            set_status(session_id, "Processing: transcribing")
            transcript = transcribe.transcribe(str(source_path))

            set_status(session_id, "Processing: segmenting")
            proposals = segment.segment(transcript)

            set_status(session_id, "Processing: persisting")
            _reconcile_snippets(session_id, proposals)

            client.table("session").update(
                {"completed_at": datetime.now(timezone.utc).isoformat()}
            ).eq("id", session_id).execute()
            set_status(session_id, "Finished")
        except NotImplementedError as exc:
            fail(session_id, str(exc))
        except Exception as exc:  # noqa: BLE001 — surface anything to the UI
            fail(session_id, f"unhandled error: {exc!s}")


def _reconcile_snippets(
    session_id: int, proposals: list[segment.ProposedSnippet]
) -> None:
    """Replace draft snippets with the new proposals; keep `is_persisted`
    rows so already-rendered URLs aren't orphaned by a re-run."""
    client = get_supabase_admin()
    client.table("snippet").delete().eq("session_id", session_id).eq(
        "is_persisted", False
    ).execute()
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
