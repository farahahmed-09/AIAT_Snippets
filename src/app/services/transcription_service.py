import os
import math
import json
import logging
import concurrent.futures
from openai import OpenAI
from moviepy.editor import VideoFileClip
from src.app.core.config import settings

logger = logging.getLogger(__name__)


def get_openai_client():
    return OpenAI(api_key=settings.OPENAI_API_KEY)


class TranscriptionService:
    @staticmethod
    def _transcribe_chunk(chunk_path: str, client: OpenAI, start_time: int) -> list:
        """Helper to transcribe a single chunk."""
        try:
            logger.debug(f"Transcribing chunk: {chunk_path}")
            with open(chunk_path, "rb") as audio_file:
                transcript_response = client.audio.translations.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"
                )

            chunk_transcripts = []
            if hasattr(transcript_response, 'segments'):
                for segment in transcript_response.segments:
                    chunk_transcripts.append({
                        "text": segment.text.strip(),
                        "start_second": round(segment.start + start_time, 3),
                        "end_second": round(segment.end + start_time, 3)
                    })
            else:
                # Fallback for non-verbose response
                chunk_transcripts.append({
                    "text": transcript_response.text,
                    "start_second": round(start_time, 3),
                    # Estimation not perfect for fallback
                    "end_second": round(start_time + 10, 3)
                })
            return chunk_transcripts
        except Exception as e:
            logger.error(
                f"Error transcribing chunk {chunk_path}: {str(e)}", exc_info=True)
            return []

    @staticmethod
    def generate_transcript_from_video(video_path: str, output_dir: str, model_name: str = "medium") -> str:
        """
        Splits video into chunks, extracts audio, sends to OpenAI API in PARALLEL, and merges transcripts.
        """
        temp_files = []
        try:
            logger.info(f"Starting transcription process for: {video_path}")

            # Load video to get duration
            clip = VideoFileClip(video_path)
            duration = clip.duration

            # Chunk settings: 20 minutes (1200 seconds)
            chunk_duration = 1200

            all_transcripts = []

            # Calculate number of chunks
            num_chunks = math.ceil(duration / chunk_duration)
            logger.info(
                f"Video duration: {duration/60:.2f} mins. Splitting into {num_chunks} chunk(s).")

            chunk_tasks = []

            # 1. Create all audio chunks sequentially (FFmpeg is CPU bound/disk bound)
            for i, start_time in enumerate(range(0, int(duration) + 1, chunk_duration)):
                end_time = min(start_time + chunk_duration, duration)
                if start_time >= end_time:
                    break

                chunk_filename = f"temp_chunk_{i}_{os.path.basename(video_path)}.mp3"
                chunk_path = os.path.join(output_dir, chunk_filename)
                temp_files.append(chunk_path)

                # Only extract if not exists (optimization) or always overwrite to be safe
                logger.info(
                    f"Extracting audio for Chunk {i+1}/{num_chunks}...")
                subclip = clip.subclip(start_time, end_time)
                subclip.audio.write_audiofile(
                    chunk_path, codec='mp3', bitrate='32k', logger=None)

                chunk_tasks.append((chunk_path, start_time))

            # Close clip after extraction
            clip.close()

            # 2. Process Transcription in Parallel
            logger.info(
                f"Starting parallel transcription for {len(chunk_tasks)} chunks...")

            # Sort results by start_time to ensure order
            results_map = {}

            client = get_openai_client()
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # We need to map futures back to their order
                future_to_index = {
                    executor.submit(TranscriptionService._transcribe_chunk, path, client, start): i
                    for i, (path, start) in enumerate(chunk_tasks)
                }

                for future in concurrent.futures.as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        data = future.result()
                        results_map[idx] = data
                        logger.debug(f"Chunk {idx+1} transcription completed.")
                    except Exception as exc:
                        logger.error(
                            f"Chunk {idx+1} generated an exception: {exc}")

            # 3. Assemble in order
            logger.info("Assembling chunks in chronological order...")
            for i in range(len(chunk_tasks)):
                if i in results_map:
                    all_transcripts.extend(results_map[i])

            # Save Final Merged JSON
            output_file = os.path.join(
                output_dir, "transcript_timestamped.json")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(all_transcripts, f, indent=2, ensure_ascii=False)

            logger.info(
                f"Transcription successfully completed. Results saved to: {output_file}")
            return output_file

        except Exception as e:
            logger.error(
                f"Transcription process failed for {video_path}: {str(e)}", exc_info=True)
            raise Exception(f"Transcription failed: {str(e)}")

        finally:
            # Cleanup: Remove all temporary chunk files
            logger.debug("Cleaning up temporary audio chunks...")
            for temp_path in temp_files:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except Exception as e:
                        logger.warning(
                            f"Failed to remove temp file {temp_path}: {e}")
