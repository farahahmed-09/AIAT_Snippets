from fastapi import HTTPException, status

from app.db.supabase import get_supabase_admin
from app.schemas.session import Session, SessionCreate, SessionUpdate
from app.services.members import _role_or_404


def _to_session(row: dict) -> Session:
    """Stringify URLs that Pydantic expects as HttpUrl."""
    return Session.model_validate(row)


def _require_membership(user_id: str, project_id: int) -> str:
    return _role_or_404(user_id, project_id)


def _require_writer(user_id: str, project_id: int) -> str:
    role = _role_or_404(user_id, project_id)
    if role not in ("manager", "editor"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Editor or manager role required")
    return role


def list_for_project(user_id: str, project_id: int) -> list[Session]:
    _require_membership(user_id, project_id)
    client = get_supabase_admin()
    rows = (
        client.table("session")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return [_to_session(r) for r in rows]


def create(user_id: str, project_id: int, payload: SessionCreate) -> Session:
    _require_writer(user_id, project_id)
    client = get_supabase_admin()
    insert = payload.model_dump(mode="json", exclude_none=True)
    insert.update(
        {
            "project_id": project_id,
            "user_id": user_id,
            "job_status": "Pending",
        }
    )
    row = client.table("session").insert(insert).execute().data[0]
    return _to_session(row)


def get(user_id: str, session_id: int) -> Session:
    row = _fetch_session_with_access(user_id, session_id)
    return _to_session(row)


def update(user_id: str, session_id: int, payload: SessionUpdate) -> Session:
    row = _fetch_session_with_access(user_id, session_id, write=True)
    patch = payload.model_dump(mode="json", exclude_none=True)
    if not patch:
        return _to_session(row)
    client = get_supabase_admin()
    updated = (
        client.table("session")
        .update(patch)
        .eq("id", session_id)
        .execute()
        .data[0]
    )
    return _to_session(updated)


def delete(user_id: str, session_id: int) -> None:
    _fetch_session_with_access(user_id, session_id, write=True)
    client = get_supabase_admin()
    client.table("session").delete().eq("id", session_id).execute()


def _fetch_session_with_access(
    user_id: str, session_id: int, *, write: bool = False
) -> dict:
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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found")
    row = rows[0]
    role = _role_or_404(user_id, row["project_id"])
    if write:
        is_owner = row["user_id"] == user_id
        if role != "manager" and not (role == "editor" and is_owner):
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Editors can only modify their own sessions",
            )
    return row
