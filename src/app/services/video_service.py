import os
import shutil
import re
import ffmpeg
import json
import textwrap
import subprocess
import requests
import asyncio
import logging
from PIL import Image, ImageDraw, ImageFont, ImageOps
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
from src.app.core.config import settings
from src.services.supabase import SupabaseService


# === ADD THIS BLOCK ===
# Monkey patch specifically for "AttributeError: module 'PIL.Image' has no attribute 'ANTIALIAS'"
if not hasattr(Image, 'ANTIALIAS'):
    Image.ANTIALIAS = Image.LANCZOS

logger = logging.getLogger(__name__)

# Defaults for fonts - assuming they are in input dir or we have fallback
FONT_GILROY_BOLD = r"src/app/fonts/Gilroy-Bold.ttf"
FONT_GILROY_REGULAR = r"src/app/fonts/Gilroy-Regular.ttf"

supabase = SupabaseService()


def run_async(coro):
    try:
        return asyncio.get_event_loop().run_until_complete(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)


class VideoService:
    @staticmethod
    def sanitize_filename(name):
        if not name:
            return "untitled"
        logger.debug(f"Sanitizing filename: {name}")
        name = re.sub(r'[ \t\n\r\f\v]+', '_', name)
        name = re.sub(r'[^\w\d_-]', '', name)
        name = name[:100].strip('_-')
        sanitized = name if name else "untitled"
        logger.debug(f"Sanitized: {sanitized}")
        return sanitized

    @staticmethod
    def clean_temp_folder(temp_dir):
        logger.debug(f"Cleaning temporary folder: {temp_dir}")
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir, exist_ok=True)

    @staticmethod
    def download_resource(url, dest_path):
        """Downloads a file from a URL to a local destination if it is a URL."""
        if not url or not url.startswith(('http:', 'https:')):
            return url  # Return as is if it's already a local path

        logger.debug(f"Downloading resource {url} to {dest_path}")
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(dest_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return dest_path
        except Exception as e:
            logger.error(f"Failed to download {url}: {e}")
            raise e

    # @classmethod
    # def process_video_with_ffmpeg(cls, video_path, json_path, output_dir, temp_dir, session_id, supabase):
    #     """
    #     Trims and concatenates source video segments based on JSON plan and applies branding.
    #     """
    #     try:
    #         logger.info(f"Starting FFmpeg processing for {video_path}")
    #         os.makedirs(output_dir, exist_ok=True)
    #         if not os.path.exists(video_path):
    #             logger.error(f"Source video not found: {video_path}")
    #             return False, f"Source video not found: {video_path}"

    #         probe = ffmpeg.probe(video_path)
    #         video_duration = float(probe['format']['duration'])

    #         with open(json_path, 'r', encoding='utf-8') as f:
    #             data = json.load(f)

    #         video_definitions = []
    #         if isinstance(data, dict):
    #             video_definitions = data.get('video_outputs', [])
    #         elif isinstance(data, list):
    #             video_definitions = data

    #         processed_count = 0
    #         for i, definition in enumerate(video_definitions):
    #             vid_title = definition.get('vid_title')
    #             output_filename = f"{i+1}) {cls.sanitize_filename(vid_title)}.mp4" if vid_title else f"{i+1}) generated_video.mp4"
    #             output_path = os.path.join(output_dir, output_filename)
    #             timestamps = definition.get('source_segment_timestamps', [])

    #             if not timestamps:
    #                 logger.warning(f"No timestamps found for {vid_title or 'video ' + str(i+1)}. Skipping.")
    #                 continue

    #             logger.info(f"Processing video: {output_filename}")
    #             cls.clean_temp_folder(temp_dir)
    #             temp_file_paths = []

    #             # Trim video segments
    #             for j, timestamp_obj in enumerate(timestamps):
    #                 start = timestamp_obj.get('start')
    #                 end = timestamp_obj.get('end')
    #                 if start is None or end is None or end <= start or start > video_duration:
    #                     logger.warning(f"Invalid timestamp range [{start}, {end}] for segment {j} of {vid_title}")
    #                     continue
    #                 if end > video_duration:
    #                     end = video_duration

    #                 temp_file_path = os.path.join(temp_dir, f"temp_{i}_{j}.mp4")
    #                 try:
    #                     logger.debug(f"Trimming segment {j}: {start} to {end}")
    #                     (
    #                         ffmpeg
    #                         .input(video_path)
    #                         # FIX: Re-encode to fix audio boundaries and ensure frame accuracy
    #                         .output(temp_file_path, ss=start, to=end, vcodec='libx264', acodec='aac', preset='ultrafast')
    #                         .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
    #                     )

    #                     temp_file_paths.append(os.path.abspath(temp_file_path))
    #                 except ffmpeg.Error as e:
    #                     logger.error(f"Failed to extract segment {j} ({start}-{end}): {e.stderr.decode()}")

    #             if not temp_file_paths:
    #                 logger.error(f"No valid segments extracted for {output_filename}")
    #                 continue

    #             # Concatenate segments into one video
    #             concat_list_path = os.path.join(temp_dir, f"concat_list_{i}.txt")
    #             try:
    #                 logger.debug(f"Creating concat list: {concat_list_path}")
    #                 with open(concat_list_path, 'w', encoding='utf-8') as f:
    #                     for path in temp_file_paths:
    #                         f.write(f"file '{path.replace(os.sep, '/')}'\n")

    #                 logger.debug(f"Concatenating segments into {output_path}")
    #                 (
    #                     ffmpeg
    #                     .input(concat_list_path, format='concat', safe=0)
    #                     .output(output_path, c='copy')
    #                     .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
    #                 )
    #                 processed_count += 1
    #                 logger.info(f"Successfully created: {output_filename}")
    #             except ffmpeg.Error as e:
    #                 logger.error(f"Error concatenating {output_filename}: {e.stderr.decode()}")

    #             cls.clean_temp_folder(temp_dir)

    #             # **Fetch session data using SupabaseService**
    #             session_data = run_async(supabase.get(table="session", filters={"id": session_id}))
    #             if session_data:
    #                 branding_data = {
    #                     "name": session_data.get("speaker_name"),
    #                     "title": session_data.get("speaker_title"),
    #                     "files": {
    #                         "profile_picture": session_data.get("speaker_image_url"),
    #                         "intro_video": session_data.get("intro_video_url"),
    #                         "background_picture": session_data.get("background_image_url")
    #                     }
    #                 }

    #                 # **Apply branding to the processed video**
    #                 branded_video_path = cls.run_ui_pipeline(output_path, branding_data, temp_dir)

    #                 # **Update the database with the branded video path**
    #                 run_async(supabase.update(table="snippet", filters={"session_id": session_id}, updates={"storage_link": branded_video_path}))
    #                 print("##########▶️▶️▶️ saved branded video path")

    #         logger.info(f"FFmpeg processing complete. Total videos produced: {processed_count}")
    #         return True, f"Processed {processed_count} videos."
    #     except Exception as e:
    #         logger.error(f"Critical error in FFmpeg processing: {str(e)}", exc_info=True)
    #         return False, f"Error: {e}"

    @classmethod
    def process_video_with_ffmpeg(cls, video_path, json_path, output_dir, temp_dir, session_id, supabase, snippet_id=None):
        """
        Trims and concatenates source video segments based on JSON plan and applies branding.
        """
        try:
            logger.info(f"Starting FFmpeg processing for {video_path}")
            os.makedirs(output_dir, exist_ok=True)
            if not os.path.exists(video_path):
                logger.error(f"Source video not found: {video_path}")
                return False, f"Source video not found: {video_path}"

            probe = ffmpeg.probe(video_path)
            video_duration = float(probe['format']['duration'])

            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            video_definitions = []
            if isinstance(data, dict):
                video_definitions = data.get('video_outputs', [])
            elif isinstance(data, list):
                video_definitions = data

            processed_count = 0
            for i, definition in enumerate(video_definitions):
                vid_title = definition.get('vid_title')
                output_filename = f"{i+1}) {cls.sanitize_filename(vid_title)}.mp4" if vid_title else f"{i+1}) generated_video.mp4"
                output_path = os.path.join(output_dir, output_filename)
                timestamps = definition.get('source_segment_timestamps', [])

                if not timestamps:
                    continue

                logger.info(f"Processing video: {output_filename}")
                cls.clean_temp_folder(temp_dir)
                temp_file_paths = []

                # Trim video segments
                for j, timestamp_obj in enumerate(timestamps):
                    start = timestamp_obj.get('start')
                    end = timestamp_obj.get('end')
                    if start is None or end is None:
                        continue
                    if end > video_duration:
                        end = video_duration

                    temp_file_path = os.path.join(
                        temp_dir, f"temp_{i}_{j}.mp4")
                    try:
                        (
                            ffmpeg
                            .input(video_path)
                            .output(temp_file_path, ss=start, to=end, vcodec='libx264', acodec='aac', preset='ultrafast')
                            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
                        )
                        temp_file_paths.append(os.path.abspath(temp_file_path))
                    except ffmpeg.Error as e:
                        logger.error(
                            f"Failed to extract segment {j}: {e.stderr.decode()}")

                if not temp_file_paths:
                    continue

                # Concatenate segments
                concat_list_path = os.path.join(
                    temp_dir, f"concat_list_{i}.txt")
                try:
                    with open(concat_list_path, 'w', encoding='utf-8') as f:
                        for path in temp_file_paths:
                            f.write(f"file '{path.replace(os.sep, '/')}'\n")

                    (
                        ffmpeg
                        .input(concat_list_path, format='concat', safe=0)
                        .output(output_path, c='copy')
                        .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
                    )
                    processed_count += 1
                except ffmpeg.Error as e:
                    logger.error(f"Error concatenating: {e.stderr.decode()}")
                    continue

                cls.clean_temp_folder(temp_dir)

                # --- BRANDING & DB UPDATE ---
                session_data = run_async(supabase.get(
                    table="session", filters={"id": session_id}))
                if session_data:
                    branding_data = {
                        "name": session_data.get("speaker_name"),
                        "title": session_data.get("speaker_title"),
                        "files": {
                            "profile_picture": session_data.get("speaker_image_url"),
                            "intro_video": session_data.get("intro_video_url"),
                            "background_picture": session_data.get("background_image_url")
                        }
                    }

                    # 1. Apply Branding
                    branded_video_path = cls.run_ui_pipeline(
                        output_path, branding_data, temp_dir)

                    # 2. Upload to Storage and Update Database
                    # Ensure we match the name used in tasks.py (vid_title or 'Untitled')
                    snippet_name = vid_title if vid_title else 'Untitled'

                    logger.info(
                        f"Uploading and saving snippet: {snippet_name}")

                    try:
                        # Upload to Supabase Storage to get a public URL
                        # We organize storage by session_id (table_id) and type
                        public_url = supabase.upload_file_to_storage(
                            resource_path=branded_video_path,
                            table_id=str(session_id),
                            resource_type="snippets"
                        )

                        # Update the SPECIFIC snippet record
                        run_async(supabase.update(
                            table="snippet",
                            filters={
                                "session_id": session_id,
                                "name": snippet_name  # Match by name to update the correct row
                            },
                            updates={"storage_link": public_url}
                        ))
                        logger.info(
                            f"✅ Database updated for snippet '{snippet_name}' with URL: {public_url}")

                    except Exception as db_err:
                        logger.error(
                            f"❌ Failed to upload/update database for {snippet_name}: {db_err}")
                # ----------------------------

            logger.info(
                f"FFmpeg processing complete. Total videos produced: {processed_count}")
            return True, f"Processed {processed_count} videos."
        except Exception as e:
            logger.error(
                f"Critical error in FFmpeg processing: {str(e)}", exc_info=True)
            return False, f"Error: {e}"

    # --- UI Processing ---
    @classmethod
    def run_ui_pipeline(cls, processed_video_path, branding_data, base_output_dir):
        """
        Runs the UI Branded Processing Pipeline.
        - `processed_video_path`: Path to the video that was trimmed in the previous step.
        - `branding_data`: Branding information (e.g., name, title, profile image, etc.) fetched from Supabase.
        - `base_output_dir`: Directory where the final branded video will be saved.
        """
        logger.info("Starting UI Branded Processing Pipeline...")

        intro_output_dir = os.path.join(base_output_dir, "intro_templates")
        stitched_output_dir = os.path.join(base_output_dir, "stitched_vids")
        final_output_dir = os.path.join(
            base_output_dir, "final_branded_videos")
        temp_dir = os.path.join(base_output_dir, "temp_ui_processing")
        os.makedirs(temp_dir, exist_ok=True)

        logger.info("Step 1/3: Generating Intros...")
        cls.generate_intros(processed_video_path,
                            intro_output_dir, branding_data, temp_dir)

        logger.info("Step 2/3: Stitching Backgrounds...")
        cls.stitch_backgrounds(processed_video_path,
                               stitched_output_dir, branding_data, temp_dir)

        logger.info("Step 3/3: Final Concatenation...")
        cls.concat_final_videos(
            intro_output_dir, stitched_output_dir, final_output_dir, temp_dir)

        logger.debug("Cleaning up UI pipeline temporary files...")
        shutil.rmtree(temp_dir, ignore_errors=True)

        final_video_path = os.path.join(final_output_dir, "final_video.mp4")
        return final_video_path

    @staticmethod
    def make_text_image(text, font_size, text_color, output_path, custom_font_path=None):
        font = ImageFont.load_default()
        if custom_font_path and os.path.exists(custom_font_path):
            try:
                font = ImageFont.truetype(custom_font_path, size=font_size)
            except:
                pass

        dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        text_width, text_height = bbox[2] - bbox[0], bbox[3] - bbox[1]

        img = Image.new('RGBA', (int(text_width) + 20,
                        int(text_height) + 20), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.text((5, 5), text, font=font, fill=text_color)
        img.save(output_path, "PNG")
        return output_path

    # @classmethod
    # def generate_intros(cls, processed_video_path, output_dir, branding_data, temp_dir):
    #     os.makedirs(output_dir, exist_ok=True)

    #     # Extract branding data (speaker name, title, profile image, intro video)
    #     name = branding_data.get("name", "User")
    #     title = branding_data.get("title", "Title")
    #     files = branding_data.get("files", {})
    #     profile_url = files.get("profile_picture")
    #     intro_video_url = files.get("intro_video")

    #     if not profile_url or not intro_video_url:
    #         logger.error("Profile picture or intro video missing in branding data.")
    #         return False

    #     try:
    #         # --- DOWNLOAD RESOURCES ---
    #         profile_path = os.path.join(temp_dir, "downloaded_profile.png")
    #         intro_video_path = os.path.join(temp_dir, "downloaded_intro.mp4")

    #         cls.download_resource(profile_url, profile_path)
    #         cls.download_resource(intro_video_url, intro_video_path)
    #         # --------------------------

    #         # Load the intro video and profile image
    #         intro_clip = VideoFileClip(intro_video_path)
    #         with Image.open(profile_path).convert("RGBA") as p_img:
    #             size = (min(p_img.size), min(p_img.size))
    #             mask = Image.new("L", size, 0)
    #             draw = ImageDraw.Draw(mask)
    #             draw.ellipse((0, 0) + size, fill=255)
    #             output_img = ImageOps.fit(p_img, size, centering=(0.5, 0.5))
    #             output_img.putalpha(mask)
    #             temp_profile_path = os.path.join(temp_dir, "temp_profile.png")
    #             output_img.save(temp_profile_path)

    #         profile_clip = ImageClip(temp_profile_path).set_duration(intro_clip.duration).resize(height=intro_clip.h * 0.5)
    #         name_clip = ImageClip(cls.make_text_image(name, 35, 'yellow', os.path.join(temp_dir, "temp_name.png"), FONT_GILROY_REGULAR)).set_duration(intro_clip.duration)
    #         title_clip = ImageClip(cls.make_text_image(title, 35, 'yellow', os.path.join(temp_dir, "temp_title.png"), FONT_GILROY_REGULAR)).set_duration(intro_clip.duration)

    #         # Set positions for overlay
    #         margin_h = 150
    #         p_x = intro_clip.w - profile_clip.w - margin_h
    #         p_y = (intro_clip.h - profile_clip.h) / 2
    #         vn_y = 650

    #         final_intro = CompositeVideoClip([intro_clip, profile_clip.set_position((p_x, p_y)), name_clip.set_position((margin_h, vn_y)), title_clip.set_position((margin_h, vn_y + name_clip.h + 10))])

    #         output_path = os.path.join(output_dir, "intro_video.mp4")
    #         final_intro.write_videofile(output_path, codec="libx264", audio_codec="aac", fps=30, verbose=False, logger=None)
    #         intro_clip.close()
    #         final_intro.close()

    #         # ==================== ADD THIS BLOCK ====================
    #         try:
    #             # This saves a copy to D:\AIAT_Snippets\src\data\input (via settings.INPUT_DIR)
    #             # We append the sanitized video name to avoid overwriting if you process multiple files
    #             vid_name = os.path.splitext(os.path.basename(processed_video_path))[0]
    #             copy_filename = f"intro_{vid_name}.mp4"

    #             # If you prefer just one static file named "intro_video.mp4", use this line instead:
    #             # copy_filename = "intro_video.mp4"

    #             destination_path = os.path.join(settings.INPUT_DIR, copy_filename)
    #             shutil.copy2(output_path, destination_path)
    #             logger.info(f"Saved copy of intro to: {destination_path}")
    #         except Exception as e:
    #             logger.error(f"Failed to copy intro to input directory: {e}")
    #         # ========================================================

    #         return output_path

    #     except Exception as e:
    #         logger.error(f"Error generating intro for {processed_video_path}: {e}")
    #         return False

    @classmethod
    def generate_intros(cls, processed_video_path, output_dir, branding_data, temp_dir):
        os.makedirs(output_dir, exist_ok=True)

        # Extract branding data
        name = branding_data.get("name", "User")
        title = branding_data.get("title", "Title")
        files = branding_data.get("files", {})
        profile_url = files.get("profile_picture")
        intro_video_url = files.get("intro_video")

        if not profile_url or not intro_video_url:
            logger.error(
                "Profile picture or intro video missing in branding data.")
            return False

        try:
            # --- DOWNLOAD RESOURCES ---
            profile_path = os.path.join(temp_dir, "downloaded_profile.png")
            intro_video_path = os.path.join(temp_dir, "downloaded_intro.mp4")

            cls.download_resource(profile_url, profile_path)
            cls.download_resource(intro_video_url, intro_video_path)
            # --------------------------

            # --- PREPARE TEXT CONTENT (Logic from ui_attachement.py) ---
            # Extract raw filename without extension for the "Video Title"
            raw_filename = os.path.basename(processed_video_path)
            raw_name_base = os.path.splitext(raw_filename)[0]

            # Clean up the text: replace underscores/dashes with spaces, Title Case
            video_name_text = raw_name_base.replace(
                "_", " ").replace("-", " ").title()

            # Wrap text if it exceeds 50 characters (matches ui_attachement logic)
            video_name_text = textwrap.fill(video_name_text, width=50)

            # Define paths for text images
            temp_vname_path = os.path.join(temp_dir, "temp_vname.png")
            temp_name_path = os.path.join(temp_dir, "temp_name.png")
            temp_title_path = os.path.join(temp_dir, "temp_title.png")

            # Generate Text Images using specific Styles and Fonts
            # 1. Video Title: Size 40, White, Gilroy-Bold
            cls.make_text_image(video_name_text, 40, 'white',
                                temp_vname_path, FONT_GILROY_BOLD)

            # 2. Name: Size 35, Yellow, Gilroy-Regular
            cls.make_text_image(name, 35, 'yellow',
                                temp_name_path, FONT_GILROY_REGULAR)

            # 3. Title/Role: Size 35, Yellow, Gilroy-Regular
            cls.make_text_image(title, 35, 'yellow',
                                temp_title_path, FONT_GILROY_REGULAR)
            # -----------------------------------------------------------

            # Load the intro video
            intro_clip = VideoFileClip(intro_video_path)

            # --- PROCESS PROFILE IMAGE (Circular Mask) ---
            with Image.open(profile_path).convert("RGBA") as p_img:
                size = (min(p_img.size), min(p_img.size))
                mask = Image.new("L", size, 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0) + size, fill=255)
                output_img = ImageOps.fit(p_img, size, centering=(0.5, 0.5))
                output_img.putalpha(mask)
                temp_profile_path = os.path.join(temp_dir, "temp_profile.png")
                output_img.save(temp_profile_path)

            # Create Clips
            profile_clip = ImageClip(temp_profile_path).set_duration(
                intro_clip.duration).resize(height=intro_clip.h * 0.5)
            vname_clip = ImageClip(temp_vname_path).set_duration(
                intro_clip.duration)
            name_clip = ImageClip(temp_name_path).set_duration(
                intro_clip.duration)
            title_clip = ImageClip(temp_title_path).set_duration(
                intro_clip.duration)

            # --- POSITIONING (Matches ui_attachement.py coordinates) ---
            margin_h = 150

            # Profile: Right side, vertically centered
            p_x = intro_clip.w - profile_clip.w - margin_h
            p_y = (intro_clip.h - profile_clip.h) / 2

            # Text Block: Left side starting at Y=650
            # 1. Video Name (Top)
            vn_x = margin_h
            vn_y = 650

            # 2. Speaker Name (Below Video Name)
            n_x = margin_h
            n_y = vn_y + vname_clip.h + 10

            # 3. Speaker Title (Below Speaker Name)
            t_x = margin_h
            t_y = n_y + name_clip.h + 10

            final_intro = CompositeVideoClip([
                intro_clip,
                profile_clip.set_position((p_x, p_y)),
                vname_clip.set_position((vn_x, vn_y)),
                name_clip.set_position((n_x, n_y)),
                title_clip.set_position((t_x, t_y))
            ])

            output_path = os.path.join(output_dir, "intro_video.mp4")
            final_intro.write_videofile(
                output_path, codec="libx264", audio_codec="aac", fps=30, verbose=False, logger=None)

            # Close clips to release resources
            intro_clip.close()
            final_intro.close()
            vname_clip.close()
            name_clip.close()
            title_clip.close()
            profile_clip.close()

            # --- OPTIONAL: SAVE COPY TO INPUT DIR ---
            try:
                vid_name = os.path.splitext(
                    os.path.basename(processed_video_path))[0]
                copy_filename = f"intro_{vid_name}.mp4"
                destination_path = os.path.join(
                    settings.INPUT_DIR, copy_filename)
                shutil.copy2(output_path, destination_path)
                logger.info(f"Saved copy of intro to: {destination_path}")
            except Exception as e:
                logger.error(f"Failed to copy intro to input directory: {e}")
            # ----------------------------------------

            return output_path

        except Exception as e:
            logger.error(
                f"Error generating intro for {processed_video_path}: {e}")
            return False

    # @classmethod
    # def stitch_backgrounds(cls, processed_video_path, output_dir, branding_data, temp_dir):
    #     os.makedirs(output_dir, exist_ok=True)

    #     # Extract branding data (background image)
    #     bg_url = branding_data.get("files", {}).get("background_picture")
    #     if not bg_url:
    #         logger.error("Background image missing in branding data.")
    #         return False

    #     # --- FIX: Download the file first ---
    #     local_bg_path = os.path.join(temp_dir, "downloaded_bg.png")
    #     try:
    #         # Check if it's a URL or local path
    #         if bg_url.startswith(('http:', 'https:')):
    #             cls.download_resource(bg_url, local_bg_path)
    #         else:
    #             # If it's already local, just copy or use it
    #             import shutil
    #             shutil.copy2(bg_url, local_bg_path)
    #     except Exception as e:
    #         logger.error(f"Failed to download background: {e}")
    #         return False
    #     # ------------------------------------

    #     temp_bg = os.path.join(temp_dir, "resized_bg.png")

    #     try:
    #         # Use local_bg_path (the downloaded file), NOT the URL
    #         with Image.open(local_bg_path) as img:
    #             img.resize((1920, 1080)).save(temp_bg)

    #         # Apply background to processed video
    #         target_video_path = os.path.join(output_dir, "stitched_video.mp4")

    #         cmd = [
    #             'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
    #             '-i', processed_video_path,
    #             '-i', temp_bg,
    #             '-filter_complex',
    #             # Ensure [1:v] has setpts=PTS-STARTPTS to fix synchronization issues
    #             '[1:v]setpts=PTS-STARTPTS[bg_reset];[0:v]setpts=PTS-STARTPTS[v_reset];'
    #             '[bg_reset][v_reset]scale2ref=w=oh*mdar:h=ih[bg][video];'
    #             '[bg]setsar=1,scale=1920:1080[bg_sized];'
    #             '[video]scale=-1:850[fg];'
    #             '[bg_sized][fg]overlay=(W-w)/2:(H-h)/2:shortest=1:format=auto',
    #             '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
    #             '-c:a', 'aac',  # <--- CRITICAL: Re-encode audio here too
    #             target_video_path
    #         ]
    #         subprocess.run(cmd)

    #         return target_video_path

    #     except Exception as e:
    #         logger.error(f"Error stitching background for {processed_video_path}: {e}")
    #         return False

    @classmethod
    def stitch_backgrounds(cls, processed_video_path, output_dir, branding_data, temp_dir):
        os.makedirs(output_dir, exist_ok=True)

        # Extract branding data (background image)
        bg_url = branding_data.get("files", {}).get("background_picture")
        if not bg_url:
            logger.error("Background image missing in branding data.")
            return False

        # --- FIX: Download or Copy the file first ---
        local_bg_path = os.path.join(temp_dir, "downloaded_bg.png")
        try:
            # Check if it's a URL or local path
            if bg_url.startswith(('http:', 'https:')):
                cls.download_resource(bg_url, local_bg_path)
            else:
                # If it's already local, just copy it to temp
                if os.path.exists(bg_url):
                    shutil.copy2(bg_url, local_bg_path)
                else:
                    logger.error(f"Local background file not found: {bg_url}")
                    return False
        except Exception as e:
            logger.error(f"Failed to download/copy background: {e}")
            return False
        # ------------------------------------

        # --- RESIZE BACKGROUND (Logic from ui_attachement.py) ---
        temp_bg = os.path.join(temp_dir, "resized_bg.png")
        try:
            with Image.open(local_bg_path) as img:
                # Use LANCZOS for high-quality downsampling
                img_resized = img.resize(
                    (1920, 1080), Image.Resampling.LANCZOS)
                img_resized.save(temp_bg)
        except Exception as e:
            logger.error(f"Error resizing background: {e}")
            return False
        # --------------------------------------------------------

        try:
            # Apply background to processed video
            target_video_path = os.path.join(output_dir, "stitched_video.mp4")

            # --- FFmpeg Command (Logic from ui_attachement.py) ---
            # Using setpts=PTS-STARTPTS to ensure overlay starts at 0
            # Scaling video to 1650 width (auto height)
            # Centering the video on the background
            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                # Input 0: Background (looped)
                '-loop', '1', '-i', temp_bg,
                '-i', processed_video_path,            # Input 1: Source Video
                '-filter_complex',
                # [1:v] source video -> reset timestamps -> scale to 1650px wide -> force 30fps -> [vid]
                '[1:v]setpts=PTS-STARTPTS,scale=1650:-1,fps=30[vid];'
                # [0:v] background -> overlay [vid] at center -> stop when shortest input ends -> [vout]
                '[0:v][vid]overlay=(W-w)/2:(H-h)/2:shortest=1[vout]',
                '-map', '[vout]',                      # Map video output
                '-map', '1:a',                         # Map audio from source video
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-c:a', 'aac', '-pix_fmt', 'yuv420p',  # Ensure compatibility
                target_video_path
            ]
            subprocess.run(cmd, check=True)
            # -----------------------------------------------------

            # ==================== ADDED: SAVE COPY ====================
            try:
                # This saves a copy to D:\AIAT_Snippets\src\data\input (via settings.INPUT_DIR)
                # We append the sanitized video name to avoid overwriting if you process multiple files
                vid_name = os.path.splitext(
                    os.path.basename(processed_video_path))[0]
                copy_filename = f"stitched_{vid_name}.mp4"

                destination_path = os.path.join(
                    settings.INPUT_DIR, copy_filename)
                shutil.copy2(target_video_path, destination_path)
                logger.info(
                    f"Saved copy of stitched video to: {destination_path}")
            except Exception as e:
                logger.error(
                    f"Failed to copy stitched video to input directory: {e}")
            # ==========================================================

            return target_video_path

        except subprocess.CalledProcessError as e:
            logger.error(
                f"FFmpeg error stitching background for {processed_video_path}: {e}")
            return False
        except Exception as e:
            logger.error(
                f"Error stitching background for {processed_video_path}: {e}")
            return False

    @classmethod
    def get_stream_info(cls, path):
        """
        Extracts detailed video and audio metadata.
        Adapted from ui_attachement.py to include audio_channels.
        """
        try:
            probe = ffmpeg.probe(path)
            video_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next(
                (s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

            if not video_stream:
                return None

            # Calculate FPS safely
            avg_frame_rate = video_stream.get('avg_frame_rate', '30/1')
            num, den = map(int, avg_frame_rate.split('/'))
            fps = num / den if den > 0 else 0

            # Audio details defaults
            audio_rate = int(
                audio_stream['sample_rate']) if audio_stream else 44100
            audio_channels = int(
                audio_stream['channels']) if audio_stream else 2
            audio_codec = audio_stream['codec_name'] if audio_stream else 'aac'

            return {
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'codec': video_stream['codec_name'],
                'fps': fps,
                'audio_rate': audio_rate,
                'audio_channels': audio_channels,
                'audio_codec': audio_codec,
                'path': path
            }
        except Exception as e:
            logger.error(f"Error reading metadata for {path}: {e}")
            return None

    @classmethod
    def concat_final_videos(cls, intro_output_dir, stitched_output_dir, output_dir, temp_dir):
        os.makedirs(output_dir, exist_ok=True)

        intro_video_path = os.path.join(intro_output_dir, "intro_video.mp4")
        stitched_video_path = os.path.join(
            stitched_output_dir, "stitched_video.mp4")

        if not os.path.exists(stitched_video_path):
            logger.error("Stitched background video not found.")
            return False

        if not os.path.exists(intro_video_path):
            logger.error("Intro video not found.")
            return False

        final_video_path = os.path.join(output_dir, "final_video.mp4")
        temp_normalized_intro = os.path.join(temp_dir, "normalized_intro.mp4")

        try:
            logger.info("Starting Final Concatenation...")

            # --- 1. ANALYZE METADATA (Logic from ui_attachement.py) ---
            v1 = cls.get_stream_info(intro_video_path)      # Intro
            v2 = cls.get_stream_info(stitched_video_path)   # Stitched (Master)

            if not v1 or not v2:
                logger.error(
                    "Metadata extraction failed. Cannot safely concatenate.")
                return False

            logger.debug(
                f"Intro: {v1['width']}x{v1['height']} {v1['fps']:.2f}fps | Main: {v2['width']}x{v2['height']} {v2['fps']:.2f}fps")

            # --- 2. CHECK MATCH & NORMALIZE ---
            properties_match = (
                v1['width'] == v2['width'] and
                v1['height'] == v2['height'] and
                abs(v1['fps'] - v2['fps']) < 0.1 and
                v1['codec'] == v2['codec'] and
                v1['audio_rate'] == v2['audio_rate'] and
                v1['audio_channels'] == v2['audio_channels']
            )

            video1_ready_path = intro_video_path

            if not properties_match:
                logger.info(
                    "⚠️ Format mismatch detected. Normalizing Intro to match Main video...")

                # Map codec names to FFmpeg encoder names (simple map)
                codec_map = {'h264': 'libx264',
                             'hevc': 'libx265', 'vp9': 'libvpx-vp9'}
                target_encoder = codec_map.get(v2['codec'], 'libx264')

                # Re-encode Intro to match Stitched exactly
                cmd_norm = [
                    'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                    '-i', intro_video_path,
                    '-vf', f"scale={v2['width']}:{v2['height']}",
                    '-r', str(v2['fps']),               # Force FPS
                    '-c:v', target_encoder,             # Match Codec
                    '-ar', str(v2['audio_rate']),       # Match Audio Rate
                    '-ac', str(v2['audio_channels']),   # Match Audio Channels
                    '-c:a', 'aac',                      # AAC is safe standard
                    '-strict', 'experimental',
                    temp_normalized_intro
                ]
                subprocess.run(cmd_norm, check=True)
                video1_ready_path = temp_normalized_intro
            else:
                logger.info("✅ Formats match. No re-encoding needed.")

            # --- 3. CONCATENATE ---
            list_file = os.path.join(temp_dir, "concat_list.txt")
            with open(list_file, "w") as f:
                f.write(f"file '{video1_ready_path}'\n")
                f.write(f"file '{stitched_video_path}'\n")

            # Use stream copy (-c copy) for speed/quality since we ensured formats match
            subprocess.run([
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-f', 'concat', '-safe', '0', '-i', list_file,
                '-c:v', 'copy', '-c:a', 'aac',
                final_video_path
            ], check=True)

            logger.info(
                f"Successfully created final video: {final_video_path}")

            # ==================== ADDED: SAVE COPY ====================
            try:
                # We attempt to find a unique name based on the stitched video if possible,
                # otherwise default to "final_video_copy.mp4"
                # (Since this method doesn't take the original filename as input, we derive or use generic)

                # Attempt to get ID from stitched filename if it follows pattern, else timestamp
                import time
                timestamp = int(time.time())
                copy_filename = f"final_video_{timestamp}.mp4"

                destination_path = os.path.join(
                    settings.INPUT_DIR, copy_filename)
                shutil.copy2(final_video_path, destination_path)
                logger.info(
                    f"Saved copy of final video to: {destination_path}")
            except Exception as e:
                logger.error(
                    f"Failed to copy final video to input directory: {e}")
            # ==========================================================

            return final_video_path

        except Exception as e:
            logger.error(f"Error concatenating intro and stitched video: {e}")
            return False
