import os
import shutil
import re
import ffmpeg
import json
import textwrap
import subprocess
import logging
from PIL import Image, ImageDraw, ImageFont, ImageOps
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip
from src.app.core.config import settings

logger = logging.getLogger(__name__)

# Defaults for fonts - assuming they are in input dir or we have fallback
FONT_GILROY_BOLD = os.path.join(settings.INPUT_DIR, "fonts", "Gilroy-Bold.ttf")
FONT_GILROY_REGULAR = os.path.join(
    settings.INPUT_DIR, "fonts", "Gilroy-Regular.ttf")


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

    @classmethod
    def process_video_with_ffmpeg(cls, video_path, json_path, output_dir, temp_dir):
        """
        Trims and concatenates source video segments based on JSON plan.
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
                    logger.warning(
                        f"No timestamps found for {vid_title or 'video ' + str(i+1)}. Skipping.")
                    continue

                logger.info(f"Processing video: {output_filename}")
                cls.clean_temp_folder(temp_dir)
                temp_file_paths = []

                for j, timestamp_obj in enumerate(timestamps):
                    start = timestamp_obj.get('start')
                    end = timestamp_obj.get('end')
                    if start is None or end is None or end <= start or start > video_duration:
                        logger.warning(
                            f"Invalid timestamp range [{start}, {end}] for segment {j} of {vid_title}")
                        continue
                    if end > video_duration:
                        end = video_duration

                    temp_file_path = os.path.join(
                        temp_dir, f"temp_{i}_{j}.mp4")
                    try:
                        logger.debug(f"Trimming segment {j}: {start} to {end}")
                        (
                            ffmpeg
                            .input(video_path)
                            .output(temp_file_path, ss=start, to=end, c='copy')
                            .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
                        )
                        temp_file_paths.append(os.path.abspath(temp_file_path))
                    except ffmpeg.Error as e:
                        logger.error(
                            f"Failed to extract segment {j} ({start}-{end}): {e.stderr.decode()}")

                if not temp_file_paths:
                    logger.error(
                        f"No valid segments extracted for {output_filename}")
                    continue

                concat_list_path = os.path.join(
                    temp_dir, f"concat_list_{i}.txt")
                try:
                    logger.debug(f"Creating concat list: {concat_list_path}")
                    with open(concat_list_path, 'w', encoding='utf-8') as f:
                        for path in temp_file_paths:
                            f.write(f"file '{path.replace(os.sep, '/')}'\n")

                    logger.debug(f"Concatenating segments into {output_path}")
                    (
                        ffmpeg
                        .input(concat_list_path, format='concat', safe=0)
                        .output(output_path, c='copy')
                        .run(capture_stdout=True, capture_stderr=True, overwrite_output=True)
                    )
                    processed_count += 1
                    logger.info(f"Successfully created: {output_filename}")
                except ffmpeg.Error as e:
                    logger.error(
                        f"Error concatenating {output_filename}: {e.stderr.decode()}")

                cls.clean_temp_folder(temp_dir)

            logger.info(
                f"FFmpeg processing complete. Total videos produced: {processed_count}")
            return True, f"Processed {processed_count} videos."
        except Exception as e:
            logger.error(
                f"Critical error in FFmpeg processing: {str(e)}", exc_info=True)
            return False, f"Error: {e}"

    # --- UI Processing ---
    @classmethod
    def run_ui_pipeline(cls, raw_videos_dir, config_data, base_output_dir):
        logger.info("Starting UI Branded Processing Pipeline...")
        intro_output_dir = os.path.join(base_output_dir, "intro_templates")
        stitched_output_dir = os.path.join(base_output_dir, "stitched_vids")
        final_output_dir = os.path.join(
            base_output_dir, "final_branded_videos")
        temp_dir = os.path.join(base_output_dir, "temp_ui_processing")
        os.makedirs(temp_dir, exist_ok=True)

        logger.info("Step 1/3: Generating Intros...")
        cls.generate_intros(raw_videos_dir, intro_output_dir,
                            config_data, temp_dir)

        logger.info("Step 2/3: Stitching Backgrounds...")
        cls.stitch_backgrounds(
            raw_videos_dir, stitched_output_dir, config_data, temp_dir)

        logger.info("Step 3/3: Final Concatenation...")
        cls.concat_final_videos(
            intro_output_dir, stitched_output_dir, final_output_dir, temp_dir)

        logger.debug("Cleaning up UI pipeline temporary files...")
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.info(
            f"UI Pipeline complete. Final videos in {final_output_dir}")
        return final_output_dir

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

    @classmethod
    def generate_intros(cls, source_dir, output_dir, config_data, temp_dir):
        os.makedirs(output_dir, exist_ok=True)
        name = config_data.get("name", "User")
        title = config_data.get("title", "Title")
        files = config_data.get("files", {})
        profile_path = files.get("profile_picture")
        intro_video_path = files.get("intro_video")

        if not profile_path or not intro_video_path:
            return False

        video_files = [f for f in os.listdir(
            source_dir) if f.endswith(('.mp4', '.avi', '.mov'))]
        for filename in video_files:
            target_path = os.path.join(output_dir, filename)
            try:
                raw_name = os.path.splitext(
                    filename)[0].replace("_", " ").title()
                video_name_text = textwrap.fill(raw_name, width=50)

                temp_name = os.path.join(temp_dir, f"t_name_{filename}.png")
                temp_title = os.path.join(temp_dir, f"t_title_{filename}.png")
                temp_vname = os.path.join(temp_dir, f"t_vname_{filename}.png")
                temp_circular = os.path.join(
                    temp_dir, f"t_prof_{filename}.png")

                cls.make_text_image(name, 35, 'yellow',
                                    temp_name, FONT_GILROY_REGULAR)
                cls.make_text_image(title, 35, 'yellow',
                                    temp_title, FONT_GILROY_REGULAR)
                cls.make_text_image(video_name_text, 40,
                                    'white', temp_vname, FONT_GILROY_BOLD)

                intro_clip = VideoFileClip(intro_video_path)
                with Image.open(profile_path).convert("RGBA") as p_img:
                    size = (min(p_img.size), min(p_img.size))
                    mask = Image.new("L", size, 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0) + size, fill=255)
                    output_img = ImageOps.fit(
                        p_img, size, centering=(0.5, 0.5))
                    output_img.putalpha(mask)
                    output_img.save(temp_circular)

                profile_clip = ImageClip(temp_circular).set_duration(
                    intro_clip.duration).resize(height=intro_clip.h * 0.5)
                name_clip = ImageClip(temp_name).set_duration(
                    intro_clip.duration)
                title_clip = ImageClip(temp_title).set_duration(
                    intro_clip.duration)
                vname_clip = ImageClip(temp_vname).set_duration(
                    intro_clip.duration)

                # Positions
                margin_h = 150
                p_x = intro_clip.w - profile_clip.w - margin_h
                p_y = (intro_clip.h - profile_clip.h) / 2
                vn_y = 650

                final_intro = CompositeVideoClip([
                    intro_clip,
                    profile_clip.set_position((p_x, p_y)),
                    vname_clip.set_position((margin_h, vn_y)),
                    name_clip.set_position(
                        (margin_h, vn_y + vname_clip.h + 10)),
                    title_clip.set_position(
                        (margin_h, vn_y + vname_clip.h + name_clip.h + 20))
                ])

                final_intro.write_videofile(
                    target_path, codec="libx264", audio_codec="aac", fps=30, verbose=False, logger=None)
                intro_clip.close()
                final_intro.close()
            except Exception as e:
                print(f"Error generating intro for {filename}: {e}")

    @classmethod
    def stitch_backgrounds(cls, source_dir, output_dir, config_data, temp_dir):
        os.makedirs(output_dir, exist_ok=True)
        bg_path = config_data.get("files", {}).get("background_picture")
        if not bg_path:
            return False

        temp_bg = os.path.join(temp_dir, "resized_bg.png")
        Image.open(bg_path).resize((1920, 1080)).save(temp_bg)

        video_files = [f for f in os.listdir(
            source_dir) if f.endswith(('.mp4', '.avi'))]
        for filename in video_files:
            source = os.path.join(source_dir, filename)
            target = os.path.join(output_dir, filename)
            cmd = [
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-loop', '1', '-i', temp_bg,
                '-i', source,
                '-filter_complex', '[1:v]setpts=PTS-STARTPTS,scale=1650:-1,fps=30[vid];[0:v][vid]overlay=(W-w)/2:(H-h)/2:shortest=1[vout]',
                '-map', '[vout]', '-map', '1:a',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-pix_fmt', 'yuv420p',
                target
            ]
            subprocess.run(cmd)

    @classmethod
    def get_stream_info(cls, path):
        try:
            probe = ffmpeg.probe(path)
            video = next(
                (s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            audio = next(
                (s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
            if not video:
                return None
            fps = eval(video.get('avg_frame_rate', '30/1'))
            return {
                'width': int(video['width']), 'height': int(video['height']), 'codec': video['codec_name'],
                'fps': fps, 'audio_rate': int(audio['sample_rate']) if audio else 44100
            }
        except:
            return None

    @classmethod
    def concat_final_videos(cls, intro_dir, stitched_dir, output_dir, temp_dir):
        os.makedirs(output_dir, exist_ok=True)
        files = [f for f in os.listdir(intro_dir) if f.endswith('.mp4')]
        for filename in files:
            intro_path = os.path.join(intro_dir, filename)
            stitched_path = os.path.join(stitched_dir, filename)
            final_path = os.path.join(output_dir, filename)
            if not os.path.exists(stitched_path):
                continue

            # Simply concat assuming format match for now or use re-encode if needed
            # For robustness in this service, I'll use the concat demuxer with re-encode fallback logic if I had more time
            # But relying on the previous logic:
            list_file = os.path.join(temp_dir, f"concat_{filename}.txt")
            with open(list_file, "w") as f:
                f.write(f"file '{intro_path}'\nfile '{stitched_path}'\n")

            subprocess.run([
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-f', 'concat', '-safe', '0', '-i', list_file,
                '-c:v', 'copy', '-c:a', 'aac', final_path
            ])
