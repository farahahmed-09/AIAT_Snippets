from celery.result import AsyncResult
from fastapi.responses import FileResponse, RedirectResponse
import os
from fastapi.responses import StreamingResponse # Add StreamingResponse
import requests # Needed if your storage_links are URLs
import zipfile
import io
from src.app.core.config import settings
from src.app.workers.tasks import generate_snippet_video
from src.app.services.storage_service import StorageManagementService
from src.services.supabase import SupabaseService
from typing import Any
from fastapi import HTTPException, APIRouter
import logging

router = APIRouter()
logger = logging.getLogger(__name__)



# @router.get("/sessions/{session_id}/download-all")
# async def download_all_snippets(session_id: int) -> Any:
#     """
#     Triggers processing for ALL snippets in a session, WAITS for them,
#     and returns a ZIP file containing the snippets' videos.
#     """
#     supabase = SupabaseService()
    
#     # 1. Fetch all snippets for the given session_id
#     response = supabase.client.table("snippet").select("*").eq("session_id", session_id).execute()
#     snippets_data = response.data
    
#     if not snippets_data:
#         raise HTTPException(status_code=404, detail="No snippets found for this session")

#     snippets = snippets_data 
    
#     logger.info(f"Found {len(snippets)} snippets for session {session_id}. IDs: {[s['id'] for s in snippets]}")

#     # 2. Trigger Generation Loop (Parallel Processing)
#     tasks = []
#     for snippet in snippets:
#         snippet_id = snippet['id']
#         logger.info(f"Starting background generation for snippet {snippet_id}")
        
#         # Fire off the Celery task (Assuming 'generate_snippet_video' is the task)
#         task = generate_snippet_video.delay(snippet_id)
#         tasks.append(task)

#     # 3. Blocking Wait (Wait for ALL to finish)
#     logger.info(f"Waiting for {len(tasks)} tasks to complete...")
#     for task in tasks:
#         try:
#             # task.get() blocks execution until that specific task is done
#             task.get() 
#         except Exception as e:
#             logger.error(f"Task generation failed: {e}")

#     logger.info("All generation tasks finished. Preparing ZIP...")

#     # 4. Re-fetch Snippets to get updated storage_link after processing
#     updated_snippets_data = await supabase.get(table="snippet", filters={"session_id": session_id})
#     snippets = updated_snippets_data if isinstance(updated_snippets_data, list) else [updated_snippets_data]

#     # 5. Create ZIP for download (this should happen after processing tasks are done)
#     zip_buffer = io.BytesIO()
#     storage_service = StorageManagementService(supabase)

#     with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
#         for snippet in snippets:
#             snippet_id = snippet['id']  # Looping over each snippet_id for this session
#             stored_path = snippet.get('storage_link')  # Get the storage link
            
#             # Create a clean filename
#             safe_name = "".join([c for c in snippet['name'] if c.isalnum() or c in (' ', '-', '_')]).strip()
#             filename = f"{safe_name}.mp4"

#             if not stored_path:
#                 zip_file.writestr(f"error_{safe_name}.txt", "Video processing failed or timed out.")
#                 continue

#             try:
#                 # --- Check if it's a Cloud URL ---
#                 if stored_path.startswith("http://") or stored_path.startswith("https://"):
#                     # If it's a URL, we simply add the URL in a text file
#                     zip_file.writestr(f"{safe_name}_url.txt", stored_path)
                
#                 # --- Handle Local File (for local file paths) ---
#                 else:
#                     if os.path.isabs(stored_path):
#                         file_path = stored_path
#                     else:
#                         file_path = os.path.join(settings.OUTPUT_DIR, str(session_id), "snippets", stored_path)

#                     # Restore if missing
#                     if not os.path.exists(file_path):
#                         await storage_service.restore_deleted_snippet_video(snippet_id)

#                     if os.path.exists(file_path):
#                         with open(file_path, "rb") as f:
#                             zip_file.writestr(filename, f.read())
#                     else:
#                         zip_file.writestr(f"error_{safe_name}.txt", "File not found locally.")

#             except Exception as e:
#                 logger.error(f"Error processing snippet {snippet_id}: {e}")
#                 zip_file.writestr(f"error_{safe_name}.txt", str(e))

#     zip_buffer.seek(0)
#     return StreamingResponse(
#         zip_buffer,
#         media_type="application/x-zip-compressed",
#         headers={"Content-Disposition": f"attachment; filename=session_{session_id}_videos.zip"}
#     )


@router.get("/sessions/{session_id}/download-all")
async def download_all_snippets(session_id: int) -> Any:
    """
    Triggers processing for ALL snippets in a session (Batch Processing).
    
    Instead of zipping, this endpoint iterates through the snippets, 
    triggers the generation task for each (if needed), and returns 
    the task details so the client can download them individually 
    once ready.
    """
    supabase = SupabaseService()
    
    # 1. Fetch all snippets for the given session_id
    response = supabase.client.table("snippet").select("*").eq("session_id", session_id).execute()
    snippets_data = response.data
    
    if not snippets_data:
        raise HTTPException(status_code=404, detail="No snippets found for this session")

    snippets = snippets_data 
    
    logger.info(f"Found {len(snippets)} snippets for session {session_id}. IDs: {[s['id'] for s in snippets]}")

    # 2. Trigger Generation Loop (Parallel Processing)
    # This adopts the looping logic from the original 'download_all' Section 2
    # and the processing logic of 'process_snippet'
    tasks_info = []
    
    for snippet in snippets:
        snippet_id = snippet['id']
        logger.info(f"Starting background generation for snippet {snippet_id}")
        
        # Fire off the Celery task
        # This mirrors the logic of triggering processing for each file
        task = generate_snippet_video.delay(snippet_id)
        
        tasks_info.append({
            "snippet_id": snippet_id,
            "name": snippet.get('name'),
            "task_id": str(task.id),
            "status": "processing_started"
        })

    logger.info(f"Triggered generation for {len(tasks_info)} snippets.")

    # Return a JSON response listing the triggered tasks. 
    # The client should now use these IDs to call /snippets/{id}/download individually.
    return {
        "message": f"Batch processing started for {len(tasks_info)} snippets.",
        "session_id": session_id,
        "results": tasks_info
    }




@router.get("/snippets/{snippet_id}/download")
async def download_snippet(snippet_id: int) -> Any:
    """
    Download the processed snippet video.
    If storage_link is a URL, redirects to it.
    If storage_link is a local path, serves the file (restoring if missing).
    """
    supabase = SupabaseService()
    snippet = await supabase.get(table="snippet", filters={"id": snippet_id})
    
    if not snippet or not snippet.get("storage_link"):
        raise HTTPException(
            status_code=404, detail="Snippet not found or not yet processed")

    stored_path = snippet['storage_link']

    # --- NEW: Check if it is a Cloud URL ---
    if stored_path.startswith("http://") or stored_path.startswith("https://"):
        # If it's a URL, we simply redirect the user to the Supabase Storage link
        return RedirectResponse(url=stored_path)
    # ---------------------------------------

    session_id = snippet['session_id']

    # Handle full path vs filename (Legacy Local File Logic)
    if os.path.isabs(stored_path):
        file_path = stored_path
    else:
        file_path = os.path.join(settings.OUTPUT_DIR, str(session_id), "snippets", stored_path)
    
    download_filename = os.path.basename(file_path)

    # If file doesn't exist locally, try to restore it
    if not os.path.exists(file_path):
        logger.info(f"Snippet file not found at {file_path}, attempting restoration")
        
        storage_service = StorageManagementService(supabase)
        
        try:
            await storage_service.restore_deleted_snippet_video(snippet_id)
            logger.info(f"Successfully restored snippet {snippet_id}")
            
            if not os.path.exists(file_path):
                logger.error(f"File still not found after restoration: {file_path}")
                raise HTTPException(status_code=404, detail="Failed to restore snippet video")
        except Exception as e:
            logger.error(f"Failed to restore snippet {snippet_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to restore snippet: {str(e)}")

    # Update access timestamp
    try:
        storage_service = StorageManagementService(supabase)
        await storage_service.update_access_timestamp(session_id)
    except Exception as e:
        logger.warning(f"Failed to update access timestamp: {e}")

    return FileResponse(
        path=file_path,
        filename=download_filename,
        media_type='video/mp4'
    )

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



