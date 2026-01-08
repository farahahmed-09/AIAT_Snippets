from fastapi import APIRouter, HTTPException
from typing import Any, List
import logging

from src.app.schemas.schemas import SessionCreate, SessionResponse, PlanUpdate, SessionUpdate, SnippetCreate
from src.app.workers.tasks import process_session_pipeline
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
