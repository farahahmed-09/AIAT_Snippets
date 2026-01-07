# import os
# import requests
# import json
# import whisper
# from urllib.parse import urlparse

# def download_video_file(url: str, output_dir: str) -> str:
#     """
#     Downloads a video file from a URL to the specified output directory.
#     Uses requests stream to handle large files.
#     """
#     try:
#         # Ensure output directory exists
#         if not os.path.exists(output_dir):
#             os.makedirs(output_dir)

#         # Get filename from URL or use default
#         path = urlparse(url).path
#         file_name = os.path.basename(path)
#         if not file_name or "." not in file_name:
#             file_name = "downloaded_video.mp4"
#         video_path = os.path.join(output_dir, file_name)
        
#         # Download stream
#         print(f"Downloading {url} to {video_path}...")
#         with requests.get(url, stream=True) as r:
#             r.raise_for_status()
#             with open(video_path, 'wb') as f:
#                 for chunk in r.iter_content(chunk_size=8192):
#                     f.write(chunk)
                    
#         return video_path
#     except Exception as e:
#         raise Exception(f"Download failed: {str(e)}")

# def generate_transcript_from_video(video_path: str, output_dir: str, model_name: str = "medium") -> str:
#     """
#     Runs the Whisper model on the video path and saves the JSON transcript.
#     Returns the path to the saved transcript file.
#     """
#     try:
#         print(f"Loading Whisper model '{model_name}'...")
#         model = whisper.load_model(model_name)

#         print(f"Transcribing {video_path}...")
#         result = model.transcribe(
#             video_path,
#             task="transcribe",
#             language=None, # auto-detect
#             word_timestamps=False
#         )

#         # Process segments into your specific format
#         all_transcripts = []
#         for seg_item in result["segments"]:
#             all_transcripts.append({
#                 "text": seg_item["text"].strip(),
#                 "start_second": round(seg_item["start"], 3),
#                 "end_second": round(seg_item["end"], 3)
#             })

#         # Save JSON
#         output_file = os.path.join(output_dir, "transcript_timestamped.json")
#         with open(output_file, "w", encoding="utf-8") as f:
#             json.dump(all_transcripts, f, indent=2, ensure_ascii=False)
            
#         return output_file

#     except Exception as e:
#         raise Exception(f"Transcription failed: {str(e)}")

import os
import requests
import json
import math
from urllib.parse import urlparse
from openai import OpenAI
from dotenv import load_dotenv
from moviepy.editor import VideoFileClip

# Load environment variables
load_dotenv()
client = OpenAI()

def download_video_file(url: str, output_dir: str) -> str:
    """
    Downloads a video file from a URL to the specified output directory.
    """
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        path = urlparse(url).path
        file_name = os.path.basename(path)
        if not file_name or "." not in file_name:
            file_name = "downloaded_video.mp4"
        video_path = os.path.join(output_dir, file_name)
        
        # Check if file already exists
        if os.path.exists(video_path):
            print(f"File {video_path} already exists. Skipping download.")
            return video_path

        print(f"Downloading {url} to {video_path}...")
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            with open(video_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
        return video_path
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")

def generate_transcript_from_video(video_path: str, output_dir: str, model_name: str = "medium") -> str:
    """
    Splits video into chunks, extracts audio, sends to OpenAI API, and merges transcripts.
    'model_name' is ignored (OpenAI API always uses whisper-1).
    """
    temp_files = []
    try:
        print(f"Processing {video_path} for transcription...")
        
        # Load video to get duration
        clip = VideoFileClip(video_path)
        duration = clip.duration
        
        # Chunk settings: 20 minutes (1200 seconds)
        chunk_duration = 1200 
        
        all_transcripts = []
        
        # Calculate number of chunks
        num_chunks = math.ceil(duration / chunk_duration)
        print(f"Video duration: {duration/60:.2f} mins. Splitting into {num_chunks} chunk(s).")

        # Iterate through chunks
        for i, start_time in enumerate(range(0, int(duration) + 1, chunk_duration)):
            end_time = min(start_time + chunk_duration, duration)
            if start_time >= end_time:
                break
                
            print(f"  - Processing Chunk {i+1}/{num_chunks} ({start_time}-{end_time}s)...")
            
            # Define chunk filename
            chunk_filename = f"temp_chunk_{i}_{os.path.basename(video_path)}.mp3"
            chunk_path = os.path.join(output_dir, chunk_filename)
            temp_files.append(chunk_path)
            
            # Extract and save audio chunk
            subclip = clip.subclip(start_time, end_time)
            subclip.audio.write_audiofile(chunk_path, codec='mp3', bitrate='32k', logger=None)
            
            # Transcribe this chunk
            with open(chunk_path, "rb") as audio_file:
                # --- CHANGE HERE: Use translations.create instead of transcriptions.create ---
                transcript_response = client.audio.translations.create(
                    model="whisper-1", 
                    file=audio_file, 
                    response_format="verbose_json"
                )
            
            # Process segments (Fixed: using dot notation instead of brackets)
            if hasattr(transcript_response, 'segments'):
                for segment in transcript_response.segments:
                    all_transcripts.append({
                        "text": segment.text.strip(),  # Fixed: .text instead of ['text']
                        # Add start_time offset to correct the timestamp relative to full video
                        "start_second": round(segment.start + start_time, 3), # Fixed: .start
                        "end_second": round(segment.end + start_time, 3)      # Fixed: .end
                    })
            else:
                # Fallback
                all_transcripts.append({
                    "text": transcript_response.text,
                    "start_second": round(start_time, 3),
                    "end_second": round(end_time, 3)
                })

        # Close the clip
        clip.close()

        # Save Final Merged JSON
        output_file = os.path.join(output_dir, "transcript_timestamped.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_transcripts, f, indent=2, ensure_ascii=False)
            
        print(f"Success! Transcript saved to: {output_file}")
        return output_file

    except Exception as e:
        raise Exception(f"Transcription failed: {str(e)}")
        
    finally:
        # Cleanup: Remove all temporary chunk files
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass