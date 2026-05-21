from fastapi import HTTPException, status

from app.db.supabase import get_supabase_admin
from app.schemas.snippet import Snippet, SnippetCreate, SnippetUpdate
from app.services.sessions import _fetch_session_with_access


def _to_snippet(row: dict) -> Snippet:
    return Snippet.model_validate(row)


def list_for_session(user_id: str, session_id: int) -> list[Snippet]:
    _fetch_session_with_access(user_id, session_id)
    client = get_supabase_admin()
    rows = (
        client.table("snippet")
        .select("*")
        .eq("session_id", session_id)
        .order("start_second", desc=False)
        .execute()
        .data
    )
    return [_to_snippet(r) for r in rows]


def get(user_id: str, snippet_id: int) -> Snippet:
    row = _load_with_access(user_id, snippet_id)
    return _to_snippet(row)


def create(user_id: str, payload: SnippetCreate) -> Snippet:
    _fetch_session_with_access(user_id, payload.session_id, write=True)
    _ensure_range(payload.start_second, payload.end_second)
    client = get_supabase_admin()
    row = (
        client.table("snippet")
        .insert(payload.model_dump(mode="json"))
        .execute()
        .data[0]
    )
    return _to_snippet(row)


def update(user_id: str, snippet_id: int, payload: SnippetUpdate) -> Snippet:
    row = _load_with_access(user_id, snippet_id, write=True)
    patch = payload.model_dump(mode="json", exclude_none=True)
    if not patch:
        return _to_snippet(row)
    start = patch.get("start_second", row["start_second"])
    end = patch.get("end_second", row["end_second"])
    _ensure_range(start, end)
    client = get_supabase_admin()
    updated = (
        client.table("snippet")
        .update(patch)
        .eq("id", snippet_id)
        .execute()
        .data[0]
    )
    return _to_snippet(updated)


def delete(user_id: str, snippet_id: int) -> None:
    _load_with_access(user_id, snippet_id, write=True)
    client = get_supabase_admin()
    client.table("snippet").delete().eq("id", snippet_id).execute()


def _load_with_access(user_id: str, snippet_id: int, *, write: bool = False) -> dict:
    client = get_supabase_admin()
    rows = (
        client.table("snippet")
        .select("*")
        .eq("id", snippet_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Snippet not found")
    snippet = rows[0]
    _fetch_session_with_access(user_id, snippet["session_id"], write=write)
    return snippet


def _ensure_range(start: int, end: int) -> None:
    if end <= start:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "end_second must be greater than start_second",
        )
