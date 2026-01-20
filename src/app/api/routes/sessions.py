from fastapi import APIRouter, HTTPException
from typing import Any, List
import logging
import base64   # <--- ADD THIS
import uuid     # <--- ADD THIS

from src.app.schemas.schemas import SessionCreate, SessionResponse, PlanUpdate, SessionUpdate, SnippetCreate
from src.app.workers.tasks import process_session_pipeline
from src.app.services.storage_service import StorageManagementService
from src.services.supabase import SupabaseService

router = APIRouter()
logger = logging.getLogger(__name__)

# --- ADD THIS HELPER FUNCTION ---
def handle_file_upload(supabase: SupabaseService, file_input: str | None, folder: str) -> str | None:
    """
    Checks if input is a Base64 string. 
    If yes: decodes it, uploads to Supabase Storage, and returns the public URL.
    If no: assumes it's already a URL and returns it as-is.
    """
    if not file_input or not file_input.startswith("data:"):
        return file_input

    try:
        # 1. Split metadata from data (e.g., "data:image/png;base64,....")
        header, encoded = file_input.split(",", 1)
        
        # 2. Extract extension (e.g., from "data:image/png;base64")
        mime_type = header.split(":")[1].split(";")[0]
        extension = mime_type.split("/")[1]
        
        # 3. Decode bytes
        file_content = base64.b64decode(encoded)
        
        # 4. Generate unique filename
        file_name = f"{uuid.uuid4()}.{extension}"
        
        # 5. Upload using your existing SupabaseService method
        public_url = supabase.upload_file_bytes_to_storage(
            file_content=file_content,
            file_name=file_name,
            folder_path=folder,
            content_type=mime_type
        )
        return public_url
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

    # --- FIX STARTS HERE: Process the files before saving ---
    # This converts the Base64 strings into actual Storage URLs
    speaker_image_url = handle_file_upload(supabase, session_in.speaker_image_url, "speaker_images")
    intro_video_url = handle_file_upload(supabase, session_in.intro_video_url, "intro_videos")
    background_image_url = handle_file_upload(supabase, session_in.background_image_url, "background_images")

    # Create Session in DB
    session_data = {
        "name": session_in.name,
        "module": session_in.module,
        "drive_link": session_in.drive_link,
        "job_status": "Pending",
        "speaker_name": session_in.speaker_name,
        "speaker_title": session_in.speaker_title,
        
        # Save the processed URLs, not the Base64 strings
        "speaker_image_url": speaker_image_url,
        "intro_video_url": intro_video_url,
        "background_image_url": background_image_url
    }
    # --- FIX ENDS HERE ---

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
        raise HTTPException(status_code=500, detail="Failed to retrieve storage statistics")


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
        raise HTTPException(status_code=500, detail="Failed to cleanup old files")


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
        raise HTTPException(status_code=500, detail=f"Failed to restore video: {str(e)}")