from fastapi import HTTPException, status

from app.db.supabase import get_supabase_admin
from app.schemas.project import Member, MemberCreate, MemberRoleUpdate, ProjectRole


def _role_or_404(user_id: str, project_id: int) -> ProjectRole:
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
    return rows[0]["role"]


def _require_manager(user_id: str, project_id: int) -> None:
    if _role_or_404(user_id, project_id) != "manager":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Manager role required")


def list_members(user_id: str, project_id: int) -> list[Member]:
    _role_or_404(user_id, project_id)  # any member can read
    client = get_supabase_admin()
    rows = (
        client.table("project_members")
        .select("user_id, role, joined_at, profiles(email, full_name, avatar_url)")
        .eq("project_id", project_id)
        .order("joined_at", desc=False)
        .execute()
        .data
    )
    return [
        Member(
            user_id=r["user_id"],
            role=r["role"],
            joined_at=r["joined_at"],
            email=(r.get("profiles") or {}).get("email"),
            full_name=(r.get("profiles") or {}).get("full_name"),
            avatar_url=(r.get("profiles") or {}).get("avatar_url"),
        )
        for r in rows
    ]


def add_member(actor_id: str, project_id: int, payload: MemberCreate) -> Member:
    _require_manager(actor_id, project_id)
    client = get_supabase_admin()
    profiles = (
        client.table("profiles")
        .select("id, email, full_name, avatar_url")
        .eq("email", payload.email)
        .limit(1)
        .execute()
        .data
    )
    if not profiles:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"No user with email {payload.email}. Ask them to sign up first.",
        )
    profile = profiles[0]
    existing = (
        client.table("project_members")
        .select("role")
        .eq("project_id", project_id)
        .eq("user_id", profile["id"])
        .limit(1)
        .execute()
        .data
    )
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "User is already a member")

    row = (
        client.table("project_members")
        .insert(
            {
                "project_id": project_id,
                "user_id": profile["id"],
                "role": payload.role,
            }
        )
        .execute()
        .data[0]
    )
    return Member(
        user_id=row["user_id"],
        role=row["role"],
        joined_at=row["joined_at"],
        email=profile.get("email"),
        full_name=profile.get("full_name"),
        avatar_url=profile.get("avatar_url"),
    )


def update_role(
    actor_id: str, project_id: int, target_user_id: str, payload: MemberRoleUpdate
) -> Member:
    _require_manager(actor_id, project_id)
    if actor_id == target_user_id and payload.role != "manager":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Managers cannot demote themselves; promote another manager first.",
        )
    client = get_supabase_admin()
    updated = (
        client.table("project_members")
        .update({"role": payload.role})
        .eq("project_id", project_id)
        .eq("user_id", target_user_id)
        .execute()
        .data
    )
    if not updated:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    return _fetch_member(project_id, target_user_id)


def remove_member(actor_id: str, project_id: int, target_user_id: str) -> None:
    if actor_id != target_user_id:
        _require_manager(actor_id, project_id)
    else:
        _role_or_404(actor_id, project_id)  # leave-self is allowed
    client = get_supabase_admin()
    client.table("project_members").delete().eq("project_id", project_id).eq(
        "user_id", target_user_id
    ).execute()


def _fetch_member(project_id: int, user_id: str) -> Member:
    client = get_supabase_admin()
    rows = (
        client.table("project_members")
        .select("user_id, role, joined_at, profiles(email, full_name, avatar_url)")
        .eq("project_id", project_id)
        .eq("user_id", user_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    r = rows[0]
    return Member(
        user_id=r["user_id"],
        role=r["role"],
        joined_at=r["joined_at"],
        email=(r.get("profiles") or {}).get("email"),
        full_name=(r.get("profiles") or {}).get("full_name"),
        avatar_url=(r.get("profiles") or {}).get("avatar_url"),
    )
