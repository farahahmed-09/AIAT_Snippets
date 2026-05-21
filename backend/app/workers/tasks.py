from app.services import pipeline
from app.workers.celery_app import celery_app


@celery_app.task(name="process_session", acks_late=True)
def process_session(session_id: int) -> dict[str, int | str]:
    pipeline.run_session_pipeline(session_id)
    return {"session_id": session_id, "status": "dispatched"}


@celery_app.task(name="render_snippet", acks_late=True)
def render_snippet(snippet_id: int) -> dict[str, int | str]:
    """Re-render a single snippet with its current trim.

    TODO: implement on top of services.render.render_snippet — download
    source + intro to /tmp, render, upload to storage, update
    snippet.storage_link.
    """
    return {"snippet_id": snippet_id, "status": "not_implemented"}
