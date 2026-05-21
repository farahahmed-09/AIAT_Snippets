from fastapi import APIRouter, status

from app.api.deps import CurrentUserDep
from app.schemas.snippet import Snippet, SnippetCreate, SnippetUpdate
from app.services import snippets
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
    # Authorisation through `get` (raises 404/403 if caller can't reach it).
    snippets.get(user.id, snippet_id)
    task = render_snippet_task.delay(snippet_id)
    return {"task_id": task.id, "status": "queued"}


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
