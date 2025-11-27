import os
import json
import shutil
import re
import sys
import ffmpeg

# Default config for processing all sections
CONFIG_SECTIONS_TO_PROCESS = -1

def sanitize_filename(name):
    """Converts a string to a safe filename."""
    if not name:
        return "untitled"
    # Replace spaces and common separators with underscores
    name = re.sub(r'[ \t\n\r\f\v]+', '_', name)
    # Remove all characters that are not alphanumeric, underscore, or hyphen
    name = re.sub(r'[^\w\d_-]', '', name)
    # Truncate to a reasonable length
    name = name[:100]
    # Remove leading/trailing underscores or hyphens
    name = name.strip('_-')
    if not name:
        return "untitled"
    return name

def clean_temp_folder(temp_dir):
    """Deletes and recreates the temporary folder."""
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)
        print(f"Temporary folder cleaned: {temp_dir}")
    except Exception as e:
        print(f"Error: Could not clean temp folder {temp_dir}. {e}")

def process_video_with_ffmpeg(video_path, json_path, output_dir, temp_dir):
    """
    Processes a source video based on a JSON file using ffmpeg-python.
    Extracts segments to a temp file, then concatenates them.
    """
    
    # 1. Ensure the output directory exists
    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"Output directory ensured: {output_dir}")
    except OSError as e:
        print(f"Error: Could not create directory {output_dir}. {e}")
        return False, str(e)

    # 2. Get Video Duration
    try:
        if not os.path.exists(video_path):
            return False, f"Source video file not found at {video_path}"

        print("Probing video file to get duration...")
        probe = ffmpeg.probe(video_path)
        video_duration = float(probe['format']['duration'])
        print(f"Source video duration: {video_duration:.2f} seconds")

    except Exception as e:
        return False, f"Could not probe video file: {e}"

    # 3. Load the JSON data
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"Successfully loaded JSON from: {json_path}")
    except Exception as e:
        return False, f"Error loading JSON: {e}"

    # --- Start of Main Processing ---
    processed_count = 0
    try:
        # 4. Get configuration
        if isinstance(data, dict):
            video_definitions = data.get('video_outputs', [])
            num_to_process = data.get('config', {}).get('sections_to_process', CONFIG_SECTIONS_TO_PROCESS)
            if num_to_process == -1: num_to_process = len(video_definitions)
        elif isinstance(data, list):
            video_definitions = data
            num_to_process = CONFIG_SECTIONS_TO_PROCESS
            if num_to_process == -1: num_to_process = len(video_definitions)
        else:
            return False, "Unexpected JSON format. Root is not a dict or a list."

        print(f"Config: Processing {num_to_process} of {len(video_definitions)} total sections.")

        # 5. Loop through and process each video section
        for i in range(min(num_to_process, len(video_definitions))):
            definition = video_definitions[i]
            vid_title = definition.get('vid_title')

            if vid_title:
                output_filename = sanitize_filename(vid_title) + ".mp4"
            else:
                output_filename = f"generated_video_{i+1}.mp4"

            timestamps = definition.get('source_segment_timestamps', [])
            output_path = os.path.join(output_dir, output_filename)

            if not timestamps:
                print(f"Warning: Skipping {output_filename} (no timestamps).")
                continue

            print(f"\n--- Processing Video {i+1}: {output_filename} ---")

            # --- STAGE 1: EXTRACT ALL CLIPS ---
            clean_temp_folder(temp_dir)
            temp_file_paths = []
            concat_list_path = os.path.join(temp_dir, f"concat_list_{i}.txt")

            for j, timestamp_obj in enumerate(timestamps):
                start = timestamp_obj.get('start')
                end = timestamp_obj.get('end')

                if start is None or end is None or end <= start:
                    continue
                
                # Validation against duration
                if start > video_duration: continue
                if end > video_duration: end = video_duration

                temp_file_path = os.path.join(temp_dir, f"temp_{i}_{j}.mp4")

                try:
                    (
                        ffmpeg
                        .input(video_path)
                        .output(temp_file_path, ss=start, to=end, c='copy')
                        .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
                    )
                    temp_file_paths.append(os.path.abspath(temp_file_path))
                except ffmpeg.Error as e:
                    print(f"FAILED to extract segment {j+1}: {e.stderr.decode()}")

            if not temp_file_paths:
                continue

            # --- STAGE 2: CONCATENATE ALL CLIPS ---
            try:
                with open(concat_list_path, 'w', encoding='utf-8') as f:
                    for path in temp_file_paths:
                        # FFmpeg concat requires forward slashes even on Windows
                        f.write(f"file '{path.replace(os.sep, '/')}'\n")

                (
                    ffmpeg
                    .input(concat_list_path, format='concat', safe=0)
                    .output(output_path, c='copy')
                    .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
                )
                processed_count += 1
                print(f"--- Successfully created {output_filename} ---")

            except ffmpeg.Error as e:
                print(f"Error during FFmpeg CONCATENATION for {output_filename}: {e.stderr.decode()}")

            # --- STAGE 3: CLEANUP ---
            clean_temp_folder(temp_dir)

    except Exception as e:
        return False, f"Unexpected error during loop: {e}"

    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

    return True, f"Processing complete. {processed_count} videos created."