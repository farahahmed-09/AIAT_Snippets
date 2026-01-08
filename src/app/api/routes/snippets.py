from celery.result import AsyncResult
from fastapi.responses import FileResponse
import os

from src.app.core.config import settings
from src.app.workers.tasks import generate_snippet_video
from src.services.supabase import SupabaseService
from typing import Any
from fastapi import HTTPException, APIRouter
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/snippets/{snippet_id}")
async def get_snippet(snippet_id: int) -> Any:
    """
    Get snippet details including storage_link status.
    """
    supabase = SupabaseService()
    snippet = await supabase.get(table="snippet", filters={"id": snippet_id})
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")
    return snippet


@router.post("/snippets/{snippet_id}/process")
async def process_snippet(
    snippet_id: int
) -> Any:
    """
    User can post process each snippet to download the snippet after styling it and adding intro.
    """
    logger.info(f"Received request to process snippet: {snippet_id}")
    supabase = SupabaseService()
    snippet = await supabase.get(table="snippet", filters={"id": snippet_id})
    if not snippet:
        logger.warning(
            f"Snippet processing failed: Snippet {snippet_id} not found.")
        raise HTTPException(status_code=404, detail="Snippet not found")

    # Trigger Celery Task
    task = generate_snippet_video.delay(snippet_id)
    logger.info(
        f"Triggered video generation for snippet {snippet_id}. Task ID: {task.id}")

    return {"message": "Snippet processing started", "task_id": str(task.id)}


@router.get("/snippets/tasks/{task_id}")
async def get_snippet_task_status(task_id: str) -> Any:
    """
    Check the status of a snippet generation task.
    """
    res = AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": res.status,
        "result": res.result if res.ready() else None
    }


@router.get("/snippets/{snippet_id}/download")
async def download_snippet(snippet_id: int) -> Any:
    """
    Download the processed snippet video.
    """
    supabase = SupabaseService()
    snippet = await supabase.get(table="snippet", filters={"id": snippet_id})
    if not snippet or not snippet.get("storage_link"):
        raise HTTPException(
            status_code=404, detail="Snippet not found or not yet processed")

    session_id = snippet['session_id']
    filename = snippet['storage_link']
    file_path = os.path.join(settings.OUTPUT_DIR, str(
        session_id), "snippets", filename)

    if not os.path.exists(file_path):
        logger.error(f"File not found at: {file_path}")
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='video/mp4'
    )
