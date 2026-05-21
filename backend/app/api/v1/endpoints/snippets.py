from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep
from app.schemas.snippet import Snippet, SnippetCreate, SnippetUpdate
from app.services import sessions as sessions_service
from app.services import snippets
from app.workers.celery_app import celery_app
from app.workers.tasks import render_snippet as render_snippet_task

# Single-snippet routes mounted at /snippets/{snippet_id}.
router = APIRouter()


@router.get("/{snippet_id}", response_model=Snippet)
def get_snippet(snippet_id: int, user: CurrentUserDep) -> Snippet:
    return snippets.get(user.id, snippet_id)


@router.patch("/{snippet_id}", response_model=Snippet)
def update_snippet(
    snippet_id: int, payload: SnippetUpdate, user: CurrentUserDep
) -> Snippet:
    return snippets.update(user.id, snippet_id, payload)


@router.delete("/{snippet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_snippet(snippet_id: int, user: CurrentUserDep) -> None:
    snippets.delete(user.id, snippet_id)


@router.post("/{snippet_id}/render")
def trigger_render(snippet_id: int, user: CurrentUserDep) -> dict[str, str]:
    # Authorisation: writer access on the snippet's session.
    snippets._load_with_access(user.id, snippet_id, write=True)
    task = render_snippet_task.delay(snippet_id)
    return {"task_id": task.id, "status": "queued"}


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str, user: CurrentUserDep) -> dict[str, object]:
    """Polling endpoint for the Celery task id returned by `/render`
    and `/process`. Mirrors the old `GET /snippets/tasks/{task_id}`.
    `user` is captured purely to keep the endpoint authenticated; task
    ids are opaque so we don't try to gate by ownership here.
    """
    _ = user
    result = celery_app.AsyncResult(task_id)
    info = result.info if isinstance(result.info, dict) else None
    payload: dict[str, object] = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
    }
    if info is not None:
        payload["info"] = info
    if result.ready():
        if result.successful():
            payload["result"] = result.result
        elif result.failed():
            payload["error"] = str(result.result)
    return payload


# Session-scoped routes mounted at /sessions/{session_id}/snippets.
session_scoped_router = APIRouter()


@session_scoped_router.get("", response_model=list[Snippet])
def list_session_snippets(
    session_id: int, user: CurrentUserDep
) -> list[Snippet]:
    return snippets.list_for_session(user.id, session_id)


@session_scoped_router.post(
    "", response_model=Snippet, status_code=status.HTTP_201_CREATED
)
def create_snippet(
    session_id: int, payload: SnippetCreate, user: CurrentUserDep
) -> Snippet:
    if payload.session_id != session_id:
        payload = payload.model_copy(update={"session_id": session_id})
    return snippets.create(user.id, payload)


@session_scoped_router.post("/render-all")
def render_all(
    session_id: int, user: CurrentUserDep
) -> dict[str, object]:
    """Fan out a render task per snippet in this session.

    Mirrors the old `GET /sessions/{id}/download-all`. Returns the list
    of dispatched task ids so the UI can poll each one.
    """
    sessions_service._fetch_session_with_access(user.id, session_id, write=True)
    items = snippets.list_for_session(user.id, session_id)
    results = [
        {"snippet_id": s.id, "task_id": render_snippet_task.delay(s.id).id}
        for s in items
    ]
    return {"session_id": session_id, "tasks": results}
