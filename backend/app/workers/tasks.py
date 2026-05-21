from app.workers.celery_app import celery_app


@celery_app.task(name="process_session")
def process_session(session_id: int) -> dict[str, int | str]:
    """Run transcription + segmentation + rendering for a session.

    TODO: port from old/src/app/workers/tasks.py.
    """
    return {"session_id": session_id, "status": "not_implemented"}
