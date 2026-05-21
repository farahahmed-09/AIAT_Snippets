from app.db.supabase import get_supabase_admin
from app.schemas.project import (
    Project,
    ProjectCreate,
    ProjectMembership,
    ProjectUpdate,
)


def list_for_user(user_id: str) -> list[ProjectMembership]:
    """Every project the user is a member of, with their role."""
    client = get_supabase_admin()
    rows = (
        client.table("project_members")
        .select("role, projects(*)")
        .eq("user_id", user_id)
        .order("joined_at", desc=False)
        .execute()
        .data
    )
    return [
        ProjectMembership(project=Project.model_validate(r["projects"]), role=r["role"])
        for r in rows
        if r.get("projects")
    ]


def create(user_id: str, payload: ProjectCreate) -> Project:
    """Insert a project; the `projects_add_manager` trigger registers
    the creator as a manager automatically."""
    client = get_supabase_admin()
    row = (
        client.table("projects")
        .insert({**payload.model_dump(), "created_by": user_id})
        .execute()
        .data[0]
    )
    return Project.model_validate(row)


def update(user_id: str, project_id: int, payload: ProjectUpdate) -> Project:
    _require_role(user_id, project_id, {"manager"})
    patch = payload.model_dump(exclude_none=True)
    if not patch:
        return get(project_id)
    client = get_supabase_admin()
    row = (
        client.table("projects")
        .update(patch)
        .eq("id", project_id)
        .execute()
        .data[0]
    )
    return Project.model_validate(row)


def delete(user_id: str, project_id: int) -> None:
    _require_role(user_id, project_id, {"manager"})
    client = get_supabase_admin()
    client.table("projects").delete().eq("id", project_id).execute()


def get(project_id: int) -> Project:
    client = get_supabase_admin()
    row = (
        client.table("projects")
        .select("*")
        .eq("id", project_id)
        .single()
        .execute()
        .data
    )
    return Project.model_validate(row)


def _require_role(user_id: str, project_id: int, allowed: set[str]) -> str:
    """Look up the caller's role in the project; raise if missing or not allowed."""
    from fastapi import HTTPException, status

    client = get_supabase_admin()
    rows = (
        client.table("project_members")
        .select("role")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    role = rows[0]["role"]
    if role not in allowed:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role in {sorted(allowed)}")
    return role
