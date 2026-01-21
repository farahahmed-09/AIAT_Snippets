from fastapi import APIRouter, HTTPException
from typing import Any, List
import logging
import base64   # <--- ADD THIS
import uuid     # <--- ADD THIS

from src.app.schemas.schemas import SessionCreate, SessionResponse, PlanUpdate, SessionUpdate, SnippetCreate, IntroUpload
from src.app.workers.tasks import process_session_pipeline
from src.app.services.storage_service import StorageManagementService
from src.services.supabase import SupabaseService
from src.app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants for file size limits
MAX_IMAGE_SIZE_MB = 5
MAX_VIDEO_SIZE_MB = 50

# --- ADD THIS HELPER FUNCTION ---


def handle_file_upload(supabase: SupabaseService, file_input: str | None, folder: str, is_video: bool = False) -> str | None:
    """
    Checks if input is a Base64 string.
    If yes: decodes it, checks size, uploads to Supabase Storage, and returns the public URL.
    If no: assumes it's already a URL and returns it as-is.
    """
    if not file_input or not file_input.startswith("data:"):
        return file_input

    # If it's a video and we want to restrict uploads
    if is_video:
        logger.warning(
            f"Direct video upload attempted for {folder}. Blocking.")
        return None

    try:
        # 1. Split metadata from data (e.g., "data:image/png;base64,....")
        header, encoded = file_input.split(",", 1)

        # 2. Extract extension (e.g., from "data:image/png;base64")
        mime_type = header.split(":")[1].split(";")[0]
        extension = mime_type.split("/")[1]

        # 3. Decode bytes
        file_content = base64.b64decode(encoded)

        # 4. Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        limit = MAX_VIDEO_SIZE_MB if is_video else MAX_IMAGE_SIZE_MB

        if file_size_mb > limit:
            logger.error(
                f"File too large: {file_size_mb:.2f}MB (Limit: {limit}MB)")
            raise HTTPException(
                status_code=413,
                detail=f"File too large ({file_size_mb:.2f}MB). Max allowed: {limit}MB"
            )

        # 5. Generate unique filename
        file_name = f"{uuid.uuid4()}.{extension}"

        # 6. Upload using your existing SupabaseService method
        public_url = supabase.upload_file_bytes_to_storage(
            file_content=file_content,
            file_name=file_name,
            folder_path=folder,
            content_type=mime_type
        )
        return public_url
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload file for {folder}: {e}")
        return None
# --------------------------------


@router.post("/upload-session")
async def upload_session(
    session_in: SessionCreate
) -> Any:
    """
    Upload Live Session endpoint.
    Accepts google drive link, validates, starts celery job.
    """
    logger.info(f"Received request to upload session: {session_in.name}")
    supabase = SupabaseService()

    # Check duplicate by drive link
    existing = await supabase.get(table="session", filters={"drive_link": session_in.drive_link})
    if existing:
        logger.warning(
            f"Session with drive link {session_in.drive_link} already exists.")
        raise HTTPException(
            status_code=400,
            detail="Session with this Drive link already exists."
        )

    # This converts the Base64 strings into actual Storage URLs
    speaker_image_url = handle_file_upload(
        supabase, session_in.speaker_image_url, "speaker_images")

    intro_video_url = handle_file_upload(
        supabase, session_in.intro_video_url, "intro_videos", is_video=True)

    background_image_url = handle_file_upload(
        supabase, session_in.background_image_url, "background_images")

    # Create Session in DB
    session_data = {
        "name": session_in.name,
        "module": session_in.module,
        "drive_link": session_in.drive_link,
        "job_status": "Pending",
        "speaker_name": session_in.speaker_name,
        "speaker_title": session_in.speaker_title,

        "speaker_image_url": speaker_image_url,
        "intro_video_url": intro_video_url,
        "background_image_url": background_image_url
    }

    new_session = await supabase.create(table="session", data=session_data)
    logger.info(f"Created new session record with ID: {new_session['id']}")

    # Start Celery Task
    process_session_pipeline.delay(new_session['id'])
    logger.info(f"Triggered background job for session: {new_session['id']}")

    return new_session


@router.get("/sessions")
async def read_sessions(
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "created_at",
    order: str = "desc"
) -> Any:
    """
    Retrieve sessions with pagination and sorting.
    """
    logger.info(f"Retrieving sessions list (skip={skip}, limit={limit})")
    supabase = SupabaseService()
    sessions = await supabase.get_all(
        table="session",
        limit=limit,
        offset=skip,
        order_by=sort_by,
        ascending=(order == "asc")
    )
    for s in sessions:
        s['video_url'] = f"/output/{s['id']}/session_video.mp4"
    return sessions


@router.get("/jobs/{session_id}/status")
async def get_job_status(session_id: int) -> Any:
    supabase = SupabaseService()
    session = await supabase.get(table="session", filters={"id": session_id})
    if not session:
        logger.warning(f"Status check failed: Session {session_id} not found.")
        raise HTTPException(status_code=404, detail="Session not found")
    return {"job_status": session.get("job_status")}


@router.get("/sessions/{session_id}/results")
async def get_session_results(session_id: int) -> Any:
    supabase = SupabaseService()
    session = await supabase.get(table="session", filters={"id": session_id})
    if not session:
        logger.warning(
            f"Results retrieval failed: Session {session_id} not found.")
        raise HTTPException(status_code=404, detail="Session not found")

    # Update access timestamp and restore if needed
    try:
        storage_service = StorageManagementService(supabase)
        await storage_service.update_access_timestamp(session_id)

        # If source video is archived, restore it for future processing
        if session.get("source_video_stored") == False:
            await storage_service.restore_deleted_session_video(session_id)
    except Exception as e:
        logger.warning(f"Storage update failed for session {session_id}: {e}")
        # Don't fail the request if storage operations fail

    # Get Snippets manually since valid ORM relationships don't exist here
    snippets = await supabase.get_all(table="snippet", filters={"session_id": session_id})
    session['snippets'] = snippets

    # Inject video_url dynamically for frontend preview
    # The file is saved during processing in process_session_pipeline
    session['video_url'] = f"/output/{session_id}/session_video.mp4"

    return session


@router.patch("/sessions/{session_id}/plan")
async def update_session_plan(
    session_id: int,
    plan_update: PlanUpdate
) -> Any:
    logger.info(
        f"Updating plan for session {session_id}. New snippets count: {len(plan_update.snippets)}")
    supabase = SupabaseService()
    session = await supabase.get(table="session", filters={"id": session_id})
    if not session:
        logger.warning(f"Plan update failed: Session {session_id} not found.")
        raise HTTPException(status_code=404, detail="Session not found")

    # Strategy: Delete existing snippets and replace with new plan
    await supabase.delete(table="snippet", filters={"session_id": session_id}, hard_delete=True)
    logger.debug(f"Cleared old snippets for session {session_id}")

    for item in plan_update.snippets:
        snippet_data = {
            "name": item.name or "Untitled",
            "summary": item.summary,
            "session_id": session_id,
            "start_second": int(item.start) if item.start is not None else 0,
            "end_second": int(item.end) if item.end is not None else 0,
        }
        await supabase.create(table="snippet", data=snippet_data)

    logger.info(f"Successfully updated plan for session {session_id}")
    return await get_session_results(session_id)


@router.get("/admin/storage-stats")
async def get_storage_stats() -> Any:
    """
    Get current storage usage statistics.
    """
    supabase = SupabaseService()
    storage_service = StorageManagementService(supabase)

    try:
        stats = await storage_service.get_storage_usage()
        return stats
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve storage statistics")


@router.post("/admin/cleanup")
async def cleanup_old_files() -> Any:
    """
    Trigger cleanup of ephemeral snippets older than 1 hour.
    """
    supabase = SupabaseService()
    storage_service = StorageManagementService(supabase)

    try:
        result = await storage_service.cleanup_ephemeral_snippets(max_age_hours=1)
        return {"message": "Cleanup completed", "result": result}
    except Exception as e:
        logger.error(f"Failed to cleanup files: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to cleanup old files")


@router.post("/admin/sessions/{session_id}/restore")
async def restore_session_video(session_id: int) -> Any:
    """
    Force restore a session's source video from Google Drive.
    """
    supabase = SupabaseService()
    session = await supabase.get(table="session", filters={"id": session_id})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    storage_service = StorageManagementService(supabase)

    try:
        result = await storage_service.restore_deleted_session_video(session_id)
        return {"message": "Session video restored", "result": result}
    except Exception as e:
        logger.error(f"Failed to restore session {session_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to restore video: {str(e)}")


@router.get("/assets/intro-videos")
async def list_intro_assets() -> Any:
    """
    List available intro videos and their corresponding thumbnails from Supabase Storage.
    """
    supabase = SupabaseService()
    try:
        # List files in assets/intro_videos
        video_files = supabase.get_files_list("assets/intro_videos")
        logger.info(f"Found {len(video_files)} intro videos")

        assets = []
        for vf in video_files:
            if not vf['name'].endswith('.mp4'):
                continue

            name_base = vf['name'].replace('.mp4', '')

            # Construct thumbnail URL (assuming same name but .png in assets/thumbnails)
            # We can also verify if it exists, but for now we follow the pattern
            thumbnail_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_BUCKET}/assets/thumbnails/{name_base}.png"

            assets.append({
                "id": name_base,
                "video_url": vf['public_url'],
                "thumbnail_url": thumbnail_url,
                "name": f"Intro {name_base}"
            })

        return assets
    except Exception as e:
        logger.error(f"Failed to list intro assets: {e}")
        raise HTTPException(
            status_code=500, detail="Failed to retrieve intro assets")


@router.post("/assets/intro-videos/upload")
async def upload_intro_video(
    intro_in: IntroUpload
) -> Any:
    """
    Upload a new intro video and its thumbnail to Supabase Storage.
    """
    supabase = SupabaseService()

    try:
        # Generate a unique ID for this asset pair
        asset_id = str(uuid.uuid4())

        # Helper to decode and upload with specific name
        def upload_named_file(base64_str, folder, name, ext):
            header, encoded = base64_str.split(",", 1)
            mime_type = header.split(":")[1].split(";")[0]
            content = base64.b64decode(encoded)
            return supabase.upload_file_bytes_to_storage(
                file_content=content,
                file_name=f"{name}.{ext}",
                folder_path=folder,
                content_type=mime_type
            )

        video_url = upload_named_file(
            intro_in.video_base64, "assets/intro_videos", asset_id, "mp4")
        thumbnail_url = upload_named_file(
            intro_in.thumbnail_base64, "assets/thumbnails", asset_id, "png")

        return {
            "id": asset_id,
            "video_url": video_url,
            "thumbnail_url": thumbnail_url,
            "name": intro_in.name
        }
    except Exception as e:
        logger.error(f"Failed to upload intro asset: {e}")
        raise HTTPException(status_code=500, detail=str(e))
