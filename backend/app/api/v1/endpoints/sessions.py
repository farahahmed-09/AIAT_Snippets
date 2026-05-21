from fastapi import APIRouter

from app.api.deps import CurrentUserDep
from app.schemas.session import Session, SessionCreate

router = APIRouter()


@router.get("", response_model=list[Session])
def list_sessions(user: CurrentUserDep) -> list[Session]:
    """List sessions for the caller's active project.

    TODO: port from old/src/app/api/routes/sessions.py. Should filter by
    project membership; the supabase admin client bypasses RLS, so the
    project scope has to be enforced here explicitly.
    """
    _ = user
    return []


@router.post("", response_model=Session, status_code=201)
def create_session(payload: SessionCreate, user: CurrentUserDep) -> Session:
    """Create a session and kick off the processing pipeline.

    TODO: port from old/src/app/api/routes/sessions.py (upload-session).
    """
    raise NotImplementedError
