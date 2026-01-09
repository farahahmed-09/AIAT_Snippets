from fastapi import APIRouter, HTTPException
from typing import Any, List
import logging

from src.app.schemas.schemas import SessionCreate, SessionResponse, PlanUpdate, SessionUpdate, SnippetCreate
from src.app.workers.tasks import process_session_pipeline
from src.app.services.storage_service import StorageManagementService
from src.services.supabase import SupabaseService

router = APIRouter()
logger = logging.getLogger(__name__)


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

    # Create Session in DB
    session_data = {
        "name": session_in.name,
        "module": session_in.module,
        "drive_link": session_in.drive_link,
        "job_status": "Pending"
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
