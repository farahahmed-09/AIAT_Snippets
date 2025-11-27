import os
import requests
import json
import whisper
from urllib.parse import urlparse

def download_video_file(url: str, output_dir: str) -> str:
    """
    Downloads a video file from a URL to the specified output directory.
    Uses requests stream to handle large files.
    """
    try:
        # Ensure output directory exists
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Get filename from URL or use default
        path = urlparse(url).path
        file_name = os.path.basename(path)
        if not file_name or "." not in file_name:
            file_name = "downloaded_video.mp4"
        video_path = os.path.join(output_dir, file_name)
        
        # Download stream
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
    Runs the Whisper model on the video path and saves the JSON transcript.
    Returns the path to the saved transcript file.
    """
    try:
        print(f"Loading Whisper model '{model_name}'...")
        model = whisper.load_model(model_name)

        print(f"Transcribing {video_path}...")
        result = model.transcribe(
            video_path,
            task="transcribe",
            language=None, # auto-detect
            word_timestamps=False
        )

        # Process segments into your specific format
        all_transcripts = []
        for seg_item in result["segments"]:
            all_transcripts.append({
                "text": seg_item["text"].strip(),
                "start_second": round(seg_item["start"], 3),
                "end_second": round(seg_item["end"], 3)
            })

        # Save JSON
        output_file = os.path.join(output_dir, "transcript_timestamped.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(all_transcripts, f, indent=2, ensure_ascii=False)
            
        return output_file

    except Exception as e:
        raise Exception(f"Transcription failed: {str(e)}")