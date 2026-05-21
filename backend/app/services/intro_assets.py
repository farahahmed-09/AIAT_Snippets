from fastapi import HTTPException, UploadFile, status

from app.db.supabase import get_supabase_admin
from app.schemas.intro_asset import IntroAsset
from app.services import storage
from app.services.members import _role_or_404


def _row_to_asset(row: dict) -> IntroAsset:
    return IntroAsset(
        id=row["id"],
        project_id=row["project_id"],
        name=row["name"],
        video_url=storage.public_url(row["video_path"]) or "",
        thumbnail_url=storage.public_url(row.get("thumbnail_path")),
        created_by=row.get("created_by"),
        created_at=row["created_at"],
    )


def list_for_project(user_id: str, project_id: int) -> list[IntroAsset]:
    _role_or_404(user_id, project_id)
    client = get_supabase_admin()
    rows = (
        client.table("intro_asset")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
        .data
    )
    return [_row_to_asset(r) for r in rows]


async def create(
    user_id: str,
    project_id: int,
    name: str,
    video: UploadFile,
    thumbnail: UploadFile | None,
) -> IntroAsset:
    role = _role_or_404(user_id, project_id)
    if role not in ("manager", "editor"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Editor or manager role required")

    if not name.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name is required")

    video_path = storage.make_intro_path(project_id, video.filename or "intro.mp4", "video")
    video_bytes = await video.read()
    storage.upload_bytes(
        video_path,
        video_bytes,
        content_type=storage.guess_content_type(
            video.filename or "intro.mp4", video.content_type or "video/mp4"
        ),
    )

    thumbnail_path = None
    if thumbnail is not None and thumbnail.filename:
        thumbnail_path = storage.make_intro_path(
            project_id, thumbnail.filename, "thumbnail"
        )
        thumb_bytes = await thumbnail.read()
        storage.upload_bytes(
            thumbnail_path,
            thumb_bytes,
            content_type=storage.guess_content_type(
                thumbnail.filename, thumbnail.content_type or "image/jpeg"
            ),
        )

    client = get_supabase_admin()
    row = (
        client.table("intro_asset")
        .insert(
            {
                "project_id": project_id,
                "name": name.strip(),
                "video_path": video_path,
                "thumbnail_path": thumbnail_path,
                "created_by": user_id,
            }
        )
        .execute()
        .data[0]
    )
    return _row_to_asset(row)


def delete(user_id: str, asset_id: int) -> None:
    client = get_supabase_admin()
    rows = (
        client.table("intro_asset")
        .select("*")
        .eq("id", asset_id)
        .limit(1)
        .execute()
        .data
    )
    if not rows:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Intro asset not found")
    asset = rows[0]
    role = _role_or_404(user_id, asset["project_id"])
    is_owner = asset.get("created_by") == user_id
    if role != "manager" and not (role == "editor" and is_owner):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Editors can only delete their own intro assets",
        )

    storage.delete_object(asset["video_path"])
    if asset.get("thumbnail_path"):
        storage.delete_object(asset["thumbnail_path"])

    client.table("intro_asset").delete().eq("id", asset_id).execute()
