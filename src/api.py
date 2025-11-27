from fastapi import FastAPI, UploadFile, File, Form, HTTPException
import os
import shutil
import json
import requests
from urllib.parse import urlparse
from dotenv import load_dotenv
from typing import Dict, Any ,List

# --- IMPORTS FROM YOUR OTHER FILES ---
from transcribe import download_video_file, generate_transcript_from_video
from Agent_snippets_generation import run_preprocessing, run_crewai_pipeline, run_postprocessing,load_json
from trim_concat import process_video_with_ffmpeg
from ui_attachement import run_ui_pipeline


# Load environment variables
load_dotenv()

app = FastAPI(title="Config & Transcript API")


# --- PATH CONFIGURATION ---
BASE_DIR = r"D:\AIAT_Snippets"
SAVE_DIRECTORY = os.path.join(BASE_DIR, "user_profile")
TRANSCRIPT_DIR = r"D:\AIAT_Snippets\input_data\transcript_timestamped.json"
OUTPUT_FOLDER_PATH = os.path.join(BASE_DIR, "output_data", "Agent_pipeline_output_files")
CONFIG_FILE = os.path.join(SAVE_DIRECTORY, "config.json")

# Specific paths for Trim/Concat
# Note: Using the video path you had hardcoded in your previous snippet, 
# or you can load it dynamically from config.json if preferred.
VIDEO_SOURCE_PATH = r"D:\AIAT_Snippets\input_data\1750962554.mp4" 
FINAL_JSON_PATH = r"D:\AIAT_Snippets\output_data\Agent_pipeline_output_files\6-final_results_mapped.json"
RAW_VIDEO_OUTPUT_DIR = r"D:\AIAT_Snippets\output_data\raw_videos_snippets"
TEMP_VIDEO_DIR = os.path.join(BASE_DIR, "temp_video_clips")

UI_OUTPUT_BASE = os.path.join(BASE_DIR, "output_data", "ui_processed")

# Constants for the pipeline
SEGMENTS_PER_CHUNK = 10  # You can adjust this based on your requirements

def save_file(file: UploadFile, destination_folder: str) -> str:
    """Helper to save uploaded form files."""
    if not file:
        return None
    file_path = os.path.join(destination_folder, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return file_path

@app.post("/configure")
async def save_configuration(
    video_link: str = Form(...),
    name: str = Form(...),
    title: str = Form(...),
    profile_picture: UploadFile = File(...),
    intro_video: UploadFile = File(...),
    background_picture: UploadFile = File(...)
):
    try:
        if not os.path.exists(SAVE_DIRECTORY):
            os.makedirs(SAVE_DIRECTORY)

        profile_path = save_file(profile_picture, SAVE_DIRECTORY)
        intro_path = save_file(intro_video, SAVE_DIRECTORY)
        bg_path = save_file(background_picture, SAVE_DIRECTORY)

        config_data = {
            "video_link": video_link,
            "name": name,
            "title": title,
            "files": {
                "profile_picture": profile_path,
                "intro_video": intro_path,
                "background_picture": bg_path
            }
        }

        with open(CONFIG_FILE, "w") as f:
            json.dump(config_data, f, indent=4)

        return {"status": "success", "message": "Configuration saved", "data": config_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/transcribe")
async def generate_transcript():
    try:
        if not os.path.exists(CONFIG_FILE):
            raise HTTPException(status_code=404, detail="Config file not found. Please run configuration first.")
        
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        
        video_url = config.get("video_link")
        if not video_url:
            raise HTTPException(status_code=400, detail="No video link found in configuration.")

        if not os.path.exists(TRANSCRIPT_DIR):
            os.makedirs(TRANSCRIPT_DIR)

        # Step A: Download
        video_file_path = download_video_file(video_url, TRANSCRIPT_DIR)

        # Step B: Transcribe
        transcript_path = generate_transcript_from_video(video_file_path, TRANSCRIPT_DIR, model_name="medium")

        # Update Config with the transcript path so the next step knows where to look
        config['transcript_path'] = transcript_path
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

        return {
            "status": "success", 
            "message": "Transcription complete", 
            "video_path": video_file_path,
            "transcript_path": transcript_path
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/processing")
async def run_processing_pipeline():
    try:
        print("--- 🚀 STARTING NEW PIPELINE RUN ---")
        
        # 1. Prepare Paths
        if not os.path.exists(OUTPUT_FOLDER_PATH):
            os.makedirs(OUTPUT_FOLDER_PATH, exist_ok=True)
            
        # 2. Set Input File (Hardcoded)
        input_file_path = TRANSCRIPT_DIR
        
        # Verify it exists
        if not os.path.exists(input_file_path):
             print(f"❌ Error: Transcript file not found at {input_file_path}")
             raise HTTPException(status_code=400, detail=f"Transcript file not found at: {input_file_path}. Please check the file path.")

        print(f"✅ Found transcript file: {input_file_path}")

        # 3. Run Pipeline Steps
        # Step A: Preprocessing
        print("Running Preprocessing...")
        if not run_preprocessing(input_file_path, OUTPUT_FOLDER_PATH, SEGMENTS_PER_CHUNK):
            raise HTTPException(status_code=500, detail="Halting execution due to pre-processing error.")

        # Step B: CrewAI Agents
        print("Running CrewAI...")
        if not run_crewai_pipeline(OUTPUT_FOLDER_PATH):
             raise HTTPException(status_code=500, detail="Halting execution due to CrewAI pipeline error.")

        # Step C: Postprocessing
        print("Running Postprocessing...")
        if not run_postprocessing(OUTPUT_FOLDER_PATH):
             raise HTTPException(status_code=500, detail="Execution finished, but post-processing failed.")

        print("\n--- ✅ NEW PIPELINE COMPLETED SUCCESSFULLY ---")

        # 4. Load Results
        final_file_path = os.path.join(OUTPUT_FOLDER_PATH, "6-final_results_mapped.json")
        final_data = {}
        
        if os.path.exists(final_file_path):
            final_data = load_json(final_file_path)
        else:
            final_data = {"warning": "Pipeline finished but final JSON not found."}

        return {
            "status": "success",
            "message": "Agent Pipeline Completed",
            "output_folder": OUTPUT_FOLDER_PATH,
            "data": final_data
        }

    except Exception as e:
        print(f"Pipeline Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trim_concat")
async def trim_and_concat_videos():
    try:
        folder_path = r"D:\AIAT_Snippets\output_data\raw_videos_snippets"
        #delete exsisting vids 
        for item in os.listdir(folder_path):
            item_path = os.path.join(folder_path, item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)        # Delete file or link
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path) 
        print("Deleted existing videos") 
        print("--- ✂️ STARTING TRIM & CONCAT ---")
        
        # 1. Determine Video Source
        # Ideally, we get this from config.json if the /transcribe step saved it there
        current_video_path = VIDEO_SOURCE_PATH # Default hardcoded fallback
        
        if os.path.exists(CONFIG_FILE):
             with open(CONFIG_FILE, 'r') as f:
                 conf = json.load(f)
                 # If /transcribe saved the local path, use it.
                 if conf.get('local_video_path') and os.path.exists(conf.get('local_video_path')):
                     current_video_path = conf.get('local_video_path')

        if not os.path.exists(current_video_path):
             raise HTTPException(status_code=404, detail=f"Source video not found at: {current_video_path}")
        
        if not os.path.exists(FINAL_JSON_PATH):
             raise HTTPException(status_code=404, detail=f"Mapped JSON results not found at: {FINAL_JSON_PATH}. Run processing first.")

        # 2. Run the Processing Function
        success, message = process_video_with_ffmpeg(
            video_path=current_video_path,
            json_path=FINAL_JSON_PATH,
            output_dir=RAW_VIDEO_OUTPUT_DIR,
            temp_dir=TEMP_VIDEO_DIR
        )

        if success:
            return {
                "status": "success",
                "message": message,
                "output_folder": RAW_VIDEO_OUTPUT_DIR
            }
        else:
            raise HTTPException(status_code=500, detail=message)

    except Exception as e:
        print(f"Trim Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/add_ui_components")
async def add_ui_components_to_videos():
    try:
        print("--- 🎨 STARTING UI ATTACHMENT PIPELINE ---")
        
        # 1. Check Config
        if not os.path.exists(CONFIG_FILE):
            raise HTTPException(status_code=404, detail="Config file missing.")

        # 2. Check Input Videos (Output from Step 4)
        if not os.path.exists(RAW_VIDEO_OUTPUT_DIR):
             raise HTTPException(status_code=404, detail=f"No raw snippets found at {RAW_VIDEO_OUTPUT_DIR}. Run Step 4 first.")

        # 3. Run Pipeline
        final_folder = run_ui_pipeline(
            raw_videos_dir=RAW_VIDEO_OUTPUT_DIR,
            config_path=CONFIG_FILE,
            base_output_dir=UI_OUTPUT_BASE
        )

        return {
            "status": "success",
            "message": "UI Components Attached Successfully",
            "output_folder": final_folder
        }

    except Exception as e:
        print(f"UI Pipeline Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/update_json_results")
async def update_json_file(updated_data: List[Dict[str, Any]]):  # <--- CHANGED Dict to List[...]
    """
    Endpoint to overwrite the final results JSON file with user edits.
    """
    try:
        if not os.path.exists(OUTPUT_FOLDER_PATH):
            raise HTTPException(status_code=404, detail="Output folder does not exist.")

        with open(FINAL_JSON_PATH, "w") as f:
            json.dump(updated_data, f, indent=4)

        return {
            "status": "success", 
            "message": "File updated successfully", 
            "data": updated_data
        }

    except Exception as e:
        print(f"Update Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)