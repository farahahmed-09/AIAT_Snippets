import os
import json
import asyncio
import logging
from celery import shared_task
from src.app.core.config import settings
from src.app.services.drive_service import DriveService
from src.app.services.transcription_service import TranscriptionService
from src.app.services.agent_service import AgentService
from src.app.services.video_service import VideoService
from src.app.core.celery_app import celery_app
from src.services.supabase import SupabaseService

logger = logging.getLogger(__name__)


def run_async(coro):
    try:
        return asyncio.get_event_loop().run_until_complete(coro)
    except RuntimeError:
        # If loop is already running or closed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


@celery_app.task(bind=True)
def process_session_pipeline(self, session_id: int):
    logger.info(f"Starting session pipeline task for session_id: {session_id}")
    supabase = SupabaseService()

    # Helper to run async methods synchronously
    def sync_update(filters, data):
        logger.debug(f"Sync update session {filters}: {data}")
        run_async(supabase.update(table="session",
                  filters=filters, updates=data))

    def sync_get(filters):
        return run_async(supabase.get(table="session", filters=filters))

    def sync_delete(filters):
        logger.debug(f"Sync delete snippets for filters: {filters}")
        run_async(supabase.delete(table="snippet",
                  filters=filters, hard_delete=True))

    def sync_create_snippet(data):
        run_async(supabase.create(table="snippet", data=data))

    session = sync_get({"id": session_id})
    if not session:
        logger.error(f"Session {session_id} not found in database.")
        return "Session not found"

    try:
        sync_update({"id": session_id}, {
                    "job_status": "Processing: Downloading"})

        # 1. Download
        video_dir = os.path.join(settings.INPUT_DIR, str(session_id))
        logger.info(
            f"Downloading video for session {session_id} to {video_dir}")
        video_path = DriveService.download_video_file(
            session['drive_link'], video_dir)

        # Move source video to output folder for static preview
        output_folder = os.path.join(settings.OUTPUT_DIR, str(session_id))
        os.makedirs(output_folder, exist_ok=True)

        # Use a stable filename for the session video preview
        session_video_filename = "session_video.mp4"
        session_video_output_path = os.path.join(
            output_folder, session_video_filename)

        # Copy to output folder (using copy instead of move to keep input for processing if needed,
        # but here we can just move if we use the new path for transcription)
        import shutil
        shutil.copy2(video_path, session_video_output_path)

        logger.info(
            f"Session video made available at: {session_video_output_path}")

        # Use the output path for transcription to ensure consistency
        video_path = session_video_output_path

        # 2. Transcribe
        sync_update({"id": session_id}, {
                    "job_status": "Processing: Transcribing"})
        logger.info(f"Generating transcript for session {session_id}")
        transcript_path = TranscriptionService.generate_transcript_from_video(
            video_path, output_folder)

        # 3. Agent Processing
        sync_update({"id": session_id}, {
                    "job_status": "Processing: Analyzing"})

        logger.info(f"Running AI preprocessing for session {session_id}")
        success = AgentService.run_preprocessing(
            transcript_path, output_folder)
        if not success:
            raise Exception("Preprocessing failed")

        logger.info(f"Running CrewAI pipeline for session {session_id}")
        success = AgentService.run_crewai_pipeline(output_folder)
        if not success:
            raise Exception("CrewAI failed")

        logger.info(f"Running postprocessing for session {session_id}")
        success = AgentService.run_postprocessing(output_folder)
        if not success:
            raise Exception("Postprocessing failed")

        # 4. Save Results to DB
        final_json_path = os.path.join(
            output_folder, "6-final_results_mapped.json")
        if os.path.exists(final_json_path):
            logger.info(
                f"Saving identified snippets for session {session_id} to database")
            with open(final_json_path, 'r', encoding='utf-8') as f:
                results = json.load(f)

            sync_delete({"session_id": session_id})

            for item in results:
                snippet_data = {
                    "name": item.get('vid_title', 'Untitled'),
                    "summary": item.get('reasoning', ''),
                    "session_id": session_id,
                    "start_second": int(item.get('start', 0)),
                    "end_second": int(item.get('end', 0))
                }
                sync_create_snippet(snippet_data)

            sync_update({"id": session_id}, {"job_status": "Finished"})
            logger.info(
                f"Session {session_id} pipeline completed successfully.")
        else:
            logger.error(f"Final results file missing at {final_json_path}")
            sync_update({"id": session_id}, {
                        "job_status": "Failed: No Results"})

    except Exception as e:
        logger.error(
            f"Pipeline failed for session {session_id}: {str(e)}", exc_info=True)
        try:
            # Truncate error message to avoid DB column limits (max 50 chars)
            error_msg = f"Failed: {str(e)}"[:49]
            sync_update({"id": session_id}, {"job_status": error_msg})
        except Exception as update_err:
            logger.error(
                f"Failed to update session status after error: {update_err}")
        raise e


@celery_app.task(bind=True)
def generate_snippet_video(self, snippet_id: int):
    logger.info(
        f"Starting snippet generation task for snippet_id: {snippet_id}")
    supabase = SupabaseService()

    def sync_get_snippet(filters):
        return run_async(supabase.get(table="snippet", filters=filters))

    def sync_get_session(filters):
        return run_async(supabase.get(table="session", filters=filters))

    snippet = sync_get_snippet({"id": snippet_id})
    if not snippet:
        logger.error(f"Snippet {snippet_id} not found.")
        return "Snippet not found"

    session = sync_get_session({"id": snippet['session_id']})
    if not session:
        logger.error(f"Session for snippet {snippet_id} not found.")
        return "Session not found"

    try:
        video_dir = os.path.join(settings.INPUT_DIR, str(session['id']))
        os.makedirs(video_dir, exist_ok=True)

        video_files = [f for f in os.listdir(
            video_dir) if f.endswith(('.mp4', '.mov'))]

        if not video_files:
            drive_link = session.get('drive_link')
            if drive_link:
                logger.info(
                    f"Source video missing locally. Downloading for snippet {snippet_id}...")
                DriveService.download_video_file(drive_link, video_dir)
                video_files = [f for f in os.listdir(
                    video_dir) if f.endswith(('.mp4', '.mov'))]

        if not video_files:
            raise Exception("Source video missing and download failed.")

        video_path = os.path.join(video_dir, video_files[0])

        plan = {
            "video_outputs": [{
                "vid_title": snippet['name'],
                "source_segment_timestamps": [{
                    "start": snippet['start_second'],
                    "end": snippet['end_second']
                }]
            }]
        }

        temp_dir = os.path.join(settings.TEMP_DIR, f"snippet_{snippet_id}")
        output_dir = os.path.join(
            settings.OUTPUT_DIR, str(session['id']), "snippets")
        plan_path = os.path.join(temp_dir, "plan.json")
        os.makedirs(temp_dir, exist_ok=True)

        with open(plan_path, 'w') as f:
            json.dump(plan, f)

        logger.info(f"Processing video for snippet {snippet_id}...")
        success, msg = VideoService.process_video_with_ffmpeg(
            video_path, plan_path, output_dir, temp_dir)

        if success:
            # Filename is generated as "1) {sanitized_title}.mp4" because we have only one output in plan
            sanitized_title = VideoService.sanitize_filename(snippet['name'])
            filename = f"1) {sanitized_title}.mp4"
            # Update storage_link in DB
            run_async(supabase.update(table="snippet", filters={
                      "id": snippet_id}, updates={"storage_link": filename}))
            logger.info(
                f"Updated snippet {snippet_id} storage_link to {filename}")

        logger.info(f"Snippet {snippet_id} generation result: {msg}")
        return msg

    except Exception as e:
        logger.error(
            f"Snippet generation failed for {snippet_id}: {str(e)}", exc_info=True)
        return f"Failed: {e}"
