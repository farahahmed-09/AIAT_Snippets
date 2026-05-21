from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUserDep
from app.schemas.session import Session, SessionCreate, SessionUpdate
from app.services import sessions
from app.workers.tasks import process_session as process_session_task

# Routes here are mounted at /sessions/* — project-scoped collection
# endpoints (list/create) live under /projects/{project_id}/sessions
# and are exposed via a separate sub-router (see router.py).
router = APIRouter()


@router.get("/{session_id}", response_model=Session)
def get_session(session_id: int, user: CurrentUserDep) -> Session:
    return sessions.get(user.id, session_id)


@router.patch("/{session_id}", response_model=Session)
def update_session(
    session_id: int, payload: SessionUpdate, user: CurrentUserDep
) -> Session:
    return sessions.update(user.id, session_id, payload)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, user: CurrentUserDep) -> None:
    row = sessions._fetch_session_with_access(user.id, session_id, write=True)
    job = row.get("job_status") or ""
    if job == "Pending" or job.startswith("Processing"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot delete a session that is currently {job}.",
        )
    sessions.delete(user.id, session_id)


@router.post("/{session_id}/process")
def trigger_processing(session_id: int, user: CurrentUserDep) -> dict[str, str]:
    # Auth gate — raises 404/403 if the caller can't write this session.
    row = sessions._fetch_session_with_access(user.id, session_id, write=True)
    job = row.get("job_status") or ""
    if job == "Pending" or job.startswith("Processing"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Session is already {job}; wait for it to finish or fail.",
        )
    task = process_session_task.delay(session_id)
    return {"task_id": task.id, "status": "queued"}


@router.post("/{session_id}/retry")
def retry_session(session_id: int, user: CurrentUserDep) -> dict[str, str]:
    """Retry a Failed session.

    Mirrors the old `/sessions/{id}/retry`: only Failed sessions are
    retriable; in-flight ones return 409 so we don't queue duplicates.
    """
    row = sessions._fetch_session_with_access(user.id, session_id, write=True)
    job = row.get("job_status") or ""
    if not job.startswith("Failed"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Only Failed sessions can be retried; current status is {job!r}.",
        )
    task = process_session_task.delay(session_id)
    return {"task_id": task.id, "status": "queued"}


# Project-scoped collection — kept in this module but mounted at
# /projects/{project_id}/sessions in router.py.
project_scoped_router = APIRouter()


@project_scoped_router.get("", response_model=list[Session])
def list_project_sessions(project_id: int, user: CurrentUserDep) -> list[Session]:
    return sessions.list_for_project(user.id, project_id)


@project_scoped_router.post(
    "", response_model=Session, status_code=status.HTTP_201_CREATED
)
def create_session(
    project_id: int, payload: SessionCreate, user: CurrentUserDep
) -> Session:
    return sessions.create(user.id, project_id, payload)
