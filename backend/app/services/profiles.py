from app.db.supabase import get_supabase_admin
from app.schemas.profile import Profile, ProfileUpdate


def get_profile(user_id: str) -> Profile:
    client = get_supabase_admin()
    row = (
        client.table("profiles")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .single()
        .execute()
        .data
    )
    return Profile.model_validate(row)


def update_profile(user_id: str, payload: ProfileUpdate) -> Profile:
    client = get_supabase_admin()
    patch = payload.model_dump(exclude_none=True)
    row = (
        client.table("profiles")
        .update(patch)
        .eq("id", user_id)
        .select("*")
        .single()
        .execute()
        .data
    )
    return Profile.model_validate(row)
