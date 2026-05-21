from fastapi import APIRouter

from app.api.deps import CurrentUserDep

router = APIRouter()


@router.post("/{snippet_id}/process")
def process_snippet(snippet_id: int, user: CurrentUserDep) -> dict[str, str]:
    """Trigger snippet rendering.

    TODO: port from old/src/app/api/routes/snippets.py.
    """
    _ = user
    raise NotImplementedError(f"process snippet {snippet_id}")
