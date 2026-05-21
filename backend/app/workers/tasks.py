"""Celery tasks for the snippet pipeline.

All artifacts (rendered clips, intermediate audio, fetched source video)
are **transient** — they live under a per-task `TemporaryDirectory` and
disappear when the task ends. The only durable home for a clip is
Supabase Storage (`services.storage.upload_*`); the persisted handle is
the public URL written back into `snippet.storage_link`.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from app.db.supabase import get_supabase_admin
from app.services import fetch, pipeline, render, source_cache, storage
from app.workers.celery_app import celery_app


logger = logging.getLogger(__name__)


@celery_app.task(name="process_session", acks_late=True)
def process_session(session_id: int) -> dict[str, int | str]:
    pipeline.run_session_pipeline(session_id)
    return {"session_id": session_id, "status": "dispatched"}


@celery_app.task(name="render_snippet", acks_late=True)
def render_snippet(snippet_id: int) -> dict[str, int | str]:
    """Render a single snippet with its current trim and persist the URL.

    Transient layout (inside a TemporaryDirectory):
        /tmp/snippet-XXXX/
            source.mp4   ← from source cache (or Drive on first call)
            intro.mp4    ← downloaded from session.intro_video_url (optional)
            out.mp4      ← ffmpeg render output

    Final state:
        - out.mp4 uploaded to Supabase Storage at
          snippets/<session_id>/<snippet_id>_<uuid>.mp4
        - snippet.storage_link = public URL of that object
        - snippet.is_persisted = True

    Re-renders pick a fresh uuid suffix so existing viewers keep
    streaming the old cut. **On failure we do NOT touch is_persisted
    or storage_link** — `_reconcile_snippets` keys off `is_persisted`
    to decide whether to drop a row on the next pipeline run, and a
    transient render failure shouldn't orphan an already-good clip.
    We re-raise so Celery marks the task FAILED and the polling
    endpoint surfaces the error to the UI.
    """
    client = get_supabase_admin()
    rows = (
        client.table("snippet")
        .select(
            "*, session(name, drive_link, intro_video_url, speaker_name, "
            "speaker_title, speaker_image_url, background_image_url)"
        )
        .eq("id", snippet_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        return {"snippet_id": snippet_id, "status": "missing"}
    snippet = rows[0]
    session = snippet.get("session") or {}

    with tempfile.TemporaryDirectory(prefix=f"snippet-{snippet_id}-") as tmp:
        workdir = Path(tmp)
        try:
            source_path = source_cache.materialise_source(
                snippet["session_id"], session["drive_link"], workdir
            )

            intro_path: Path | None = None
            if session.get("intro_video_url"):
                intro_path = workdir / "intro.mp4"
                fetch.fetch_to_disk(session["intro_video_url"], intro_path)

            speaker_image_path: Path | None = None
            if session.get("speaker_image_url"):
                speaker_image_path = workdir / "speaker.png"
                fetch.fetch_to_disk(session["speaker_image_url"], speaker_image_path)

            output_path = workdir / "out.mp4"
            render.render_snippet(
                render.RenderInputs(
                    source_video_path=str(source_path),
                    start_second=snippet["start_second"],
                    end_second=snippet["end_second"],
                    intro_video_path=str(intro_path) if intro_path else None,
                    speaker_name=session.get("speaker_name"),
                    speaker_title=session.get("speaker_title"),
                    speaker_image_path=(
                        str(speaker_image_path) if speaker_image_path else None
                    ),
                    background_image_path=None,
                    video_title=snippet.get("name") or session.get("name"),
                ),
                output_path=str(output_path),
            )

            key = storage.make_snippet_path(snippet["session_id"], snippet_id)
            storage.upload_file(key, str(output_path), content_type="video/mp4")
            public_url = storage.public_url(key)

            client.table("snippet").update(
                {"storage_link": public_url, "is_persisted": True}
            ).eq("id", snippet_id).execute()

            return {"snippet_id": snippet_id, "status": "rendered"}
        except Exception:
            logger.exception(
                "render_snippet failed", extra={"snippet_id": snippet_id}
            )
            raise
