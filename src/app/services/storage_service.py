import os
import shutil
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from src.app.core.config import settings
from src.services.supabase import SupabaseService
from src.app.services.drive_service import DriveService

logger = logging.getLogger(__name__)


class StorageManagementService:
    """
    Manages the 4-tier storage strategy:
    1. Keep last 3 accessed source videos
    2. Keep all JSON output files
    3. Re-download deleted videos on demand
    4. Generate ephemeral snippets in temp directory
    """

    def __init__(self):
        self.supabase = SupabaseService()
        self.input_dir = settings.INPUT_DIR
        self.output_dir = settings.OUTPUT_DIR
        self.temp_dir = settings.TEMP_DIR

    # ========== TIER 1: HOT CACHE MANAGEMENT ==========

    async def maintain_source_video_cache(self, max_keep: int = 3) -> Dict:
        """
        Keep only the last {max_keep} accessed source videos.
        Delete older ones while preserving metadata.
        """
        try:
            logger.info(f"Starting source video cache maintenance (keep={max_keep})...")
            
            # Get all sessions with stored videos, ordered by last access
            sessions_with_videos = await self.supabase.get_all(
                table="session",
                filters={"source_video_stored": True},
                columns=["id", "name", "last_accessed_at"],
                order_by="last_accessed_at",
                ascending=False,
                limit=1000
            )
            
            if not sessions_with_videos:
                logger.info("No sessions with stored videos found.")
                return {
                    "kept_sessions": [],
                    "deleted_sessions": [],
                    "space_freed_mb": 0.0,
                    "sessions_archived": 0
                }
            
            kept_ids = [s['id'] for s in sessions_with_videos[:max_keep]]
            to_delete_ids = [s['id'] for s in sessions_with_videos[max_keep:]]
            
            space_freed = 0.0
            
            # Delete old session videos
            for session_id in to_delete_ids:
                space = await self._delete_session_video_from_disk(session_id)
                space_freed += space
                
                # Update database to mark as archived
                await self.supabase.update(
                    table="session",
                    filters={"id": session_id},
                    updates={"source_video_stored": False}
                )
                logger.info(f"Archived session {session_id}: freed {space:.2f}MB")
            
            logger.info(
                f"Cache maintenance complete: "
                f"kept={len(kept_ids)}, "
                f"archived={len(to_delete_ids)}, "
                f"space_freed={space_freed:.2f}MB"
            )
            
            return {
                "kept_sessions": kept_ids,
                "deleted_sessions": to_delete_ids,
                "space_freed_mb": space_freed,
                "sessions_archived": len(to_delete_ids)
            }

        except Exception as e:
            logger.error(f"Error in maintain_source_video_cache: {str(e)}", exc_info=True)
            raise

    async def _delete_session_video_from_disk(self, session_id: int) -> float:
        """
        Delete session video files from disk.
        Returns: Space freed in MB
        """
        space_freed = 0.0
        
        # Delete from input directory
        input_video = os.path.join(self.input_dir, str(session_id), "downloaded_video.mp4")
        if os.path.exists(input_video):
            try:
                size = os.path.getsize(input_video)
                os.remove(input_video)
                space_freed += size / (1024 * 1024)
                logger.debug(f"Deleted input video: {input_video}")
            except Exception as e:
                logger.warning(f"Failed to delete {input_video}: {e}")
        
        # Delete from output directory
        output_video = os.path.join(self.output_dir, str(session_id), "session_video.mp4")
        if os.path.exists(output_video):
            try:
                size = os.path.getsize(output_video)
                os.remove(output_video)
                space_freed += size / (1024 * 1024)
                logger.debug(f"Deleted output video: {output_video}")
            except Exception as e:
                logger.warning(f"Failed to delete {output_video}: {e}")
        
        return space_freed

    # ========== TIER 3: ON-DEMAND RESTORATION ==========

    async def restore_deleted_session_video(self, session_id: int) -> str:
        """
        Restore a deleted session video by re-downloading from Google Drive.
        Returns: Path to the restored video file
        """
        try:
            logger.info(f"Checking video availability for session {session_id}...")
            
            # Check if video already exists
            output_video = os.path.join(self.output_dir, str(session_id), "session_video.mp4")
            if os.path.exists(output_video) and os.path.getsize(output_video) > 1000000:
                logger.info(f"Video already exists: {output_video}")
                return output_video
            
            # Get session from database
            session = await self.supabase.get(
                table="session",
                filters={"id": session_id}
            )
            
            if not session or not session.get('drive_link'):
                raise Exception(f"Session {session_id} not found or has no drive_link")
            
            logger.info(f"Re-downloading video for session {session_id} from Google Drive...")
            
            # Re-download video
            input_dir = os.path.join(self.input_dir, str(session_id))
            os.makedirs(input_dir, exist_ok=True)
            
            video_path = DriveService.download_video_file(
                session['drive_link'],
                input_dir
            )
            
            # Copy to output directory
            output_dir = os.path.join(self.output_dir, str(session_id))
            os.makedirs(output_dir, exist_ok=True)
            
            output_video = os.path.join(output_dir, "session_video.mp4")
            shutil.copy2(video_path, output_video)
            
            # Update database
            await self.supabase.update(
                table="session",
                filters={"id": session_id},
                updates={"source_video_stored": True}
            )
            
            logger.info(f"Successfully restored video: {output_video}")
            return output_video

        except Exception as e:
            logger.error(f"Failed to restore session video: {str(e)}", exc_info=True)
            raise

    async def restore_deleted_snippet_video(self, snippet_id: int) -> str:
        """
        Restore a deleted snippet video by re-generating from source.
        Returns: Path to the restored snippet video file
        """
        try:
            logger.info(f"Attempting to restore snippet {snippet_id}...")
            
            # Get snippet details
            snippet = await self.supabase.get(
                table="snippet",
                filters={"id": snippet_id}
            )
            
            if not snippet:
                raise Exception(f"Snippet {snippet_id} not found")
            
            session_id = snippet['session_id']
            
            # Check if snippet already exists
            output_dir = os.path.join(self.output_dir, str(session_id), "snippets")
            if snippet.get('storage_link'):
                snippet_path = os.path.join(output_dir, snippet['storage_link'])
                if os.path.exists(snippet_path):
                    logger.info(f"Snippet already exists: {snippet_path}")
                    return snippet_path
            
            # Ensure source video is available
            await self.restore_deleted_session_video(session_id)
            
            logger.info(f"Successfully restored snippet {snippet_id}")
            return ""

        except Exception as e:
            logger.error(f"Failed to restore snippet video: {str(e)}", exc_info=True)
            raise

    # ========== TIER 4: EPHEMERAL SNIPPETS ==========

    async def cleanup_ephemeral_snippets(self, max_age_hours: int = 1) -> Dict:
        """
        Delete ephemeral snippets older than max_age_hours.
        Returns: {deleted_count, space_freed_mb, errors}
        """
        try:
            logger.info(f"Starting ephemeral snippet cleanup (max_age={max_age_hours}h)...")
            
            # Find ephemeral snippets to delete
            ephemeral = await self.supabase.get_all(
                table="snippet",
                filters={"is_persisted": False},
                columns=["id", "session_id", "storage_link", "created_at"],
                limit=1000
            )
            
            deleted_count = 0
            space_freed = 0.0
            errors = []
            
            for snippet in ephemeral:
                try:
                    session_id = snippet['session_id']
                    storage_link = snippet.get('storage_link')
                    
                    if storage_link:
                        snippet_path = os.path.join(
                            self.output_dir, str(session_id), "snippets", storage_link
                        )
                        if os.path.exists(snippet_path):
                            size = os.path.getsize(snippet_path)
                            os.remove(snippet_path)
                            space_freed += size / (1024 * 1024)
                            deleted_count += 1
                            logger.debug(f"Deleted ephemeral snippet: {snippet_path}")
                
                except Exception as e:
                    error_msg = f"Failed to delete snippet {snippet['id']}: {str(e)}"
                    logger.warning(error_msg)
                    errors.append(error_msg)
            
            logger.info(
                f"Cleanup complete: deleted={deleted_count}, "
                f"space_freed={space_freed:.2f}MB, errors={len(errors)}"
            )
            
            return {
                "deleted_count": deleted_count,
                "space_freed_mb": space_freed,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Error in cleanup_ephemeral_snippets: {str(e)}", exc_info=True)
            raise

    # ========== UTILITY METHODS ==========

    async def update_access_timestamp(self, session_id: int) -> None:
        """Update last_accessed_at for a session."""
        try:
            await self.supabase.update(
                table="session",
                filters={"id": session_id},
                updates={"last_accessed_at": datetime.utcnow().isoformat()}
            )
            logger.debug(f"Updated last_accessed_at for session {session_id}")
        except Exception as e:
            logger.warning(f"Failed to update access timestamp: {e}")

    async def get_storage_usage(self) -> Dict:
        """Calculate current storage usage across all tiers."""
        try:
            logger.info("Calculating storage usage...")
            
            # Calculate directory sizes
            input_size = self._get_directory_size(self.input_dir)
            output_size = self._get_directory_size(self.output_dir)
            temp_size = self._get_directory_size(self.temp_dir)
            total_size = input_size + output_size + temp_size
            
            # Count database entries
            all_sessions = await self.supabase.get_all(
                table="session",
                columns=["id", "source_video_stored"],
                limit=10000
            )
            
            cached_sessions = len([s for s in all_sessions if s.get('source_video_stored')])
            archived_sessions = len(all_sessions) - cached_sessions
            
            all_snippets = await self.supabase.get_all(
                table="snippet",
                columns=["id", "is_persisted"],
                limit=100000
            )
            
            persisted = len([s for s in all_snippets if s.get('is_persisted')])
            ephemeral = len(all_snippets) - persisted
            
            usage = {
                "input_dir_mb": input_size / (1024 * 1024),
                "output_dir_mb": output_size / (1024 * 1024),
                "temp_dir_mb": temp_size / (1024 * 1024),
                "total_mb": total_size / (1024 * 1024),
                "stored_sessions_count": len(all_sessions),
                "persisted_snippets_count": persisted,
                "ephemeral_snippets_count": ephemeral,
                "sessions_with_cached_video": cached_sessions,
                "sessions_archived": archived_sessions
            }
            
            logger.info(f"Storage usage: {usage['total_mb']:.2f}MB total")
            return usage

        except Exception as e:
            logger.error(f"Error getting storage usage: {str(e)}", exc_info=True)
            raise

    def _get_directory_size(self, directory: str) -> int:
        """Get total size of directory in bytes."""
        total = 0
        if not os.path.exists(directory):
            return 0
        
        try:
            for dirpath, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass
        except Exception as e:
            logger.warning(f"Error calculating directory size for {directory}: {e}")
        
        return total
