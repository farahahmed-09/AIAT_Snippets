import os
import shutil
import math
import subprocess
import ffmpeg
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps
from moviepy.editor import *
import textwrap

# --- DEFAULTS ---
# Update these paths to where your fonts actually live locally, or keep them relative
FONT_GILROY_BOLD = r"D:\AIAT_Snippets\input_data\fonts\Gilroy-Bold.ttf" 
FONT_GILROY_REGULAR = r"D:\AIAT_Snippets\input_data\fonts\Gilroy-Regular.ttf"

def make_text_image(text, font_size, text_color, output_path, custom_font_path=None):
    """Creates a transparent PNG image with the given text."""
    font = None
    
    # 1. Try Custom Font
    if custom_font_path and os.path.exists(custom_font_path):
        try:
            font = ImageFont.truetype(custom_font_path, size=font_size)
        except IOError:
            print(f"Could not load custom font at {custom_font_path}.")

    # 2. Fallback
    if font is None:
        font = ImageFont.load_default()

    # # Get bounding box
    # if hasattr(font, 'getbbox'):
    #     bbox = font.getbbox(text)
    #     text_width = bbox[2] - bbox[0]
    #     text_height = bbox[3] - bbox[1]
    #     text_pos = (5, 5)
    # else:
    #     text_width = font.getlength(text)
    #     text_height = 10
    #     text_pos = (10, 0)


    # Use textbbox to calculate size (supports multiline)
    dummy_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
    bbox = dummy_draw.textbbox((0, 0), text, font=font)
    
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_pos = (5, 5)

    img_width = int(text_width) + 20
    img_height = int(text_height) + 20
    img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text(text_pos, text, font=font, fill=text_color)
    img.save(output_path, "PNG")
    return output_path

def generate_intros(source_dir, output_dir, config_data, temp_dir):
    """
    Generates intro videos based on profile pic, name, title, and intro video template.
    Corresponds to Colab Part 1.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # Extract config
    name = config_data.get("name", "User")
    title = config_data.get("title", "Title")
    files = config_data.get("files", {})
    profile_path = files.get("profile_picture")
    intro_video_path = files.get("intro_video")

    if not profile_path or not intro_video_path or not os.path.exists(profile_path) or not os.path.exists(intro_video_path):
        print("Missing profile picture or intro video in config.")
        return False

    video_files = [f for f in os.listdir(source_dir) if f.endswith(('.mp4', '.avi', '.mov', '.mkv'))]
    
    for filename in video_files:
        print(f"Generating Intro for: {filename}")
        target_intro_path = os.path.join(output_dir, filename)
        
        # Temp paths
        temp_circular = os.path.join(temp_dir, f"temp_profile_{filename}.png")
        temp_name = os.path.join(temp_dir, f"temp_name_{filename}.png")
        temp_title = os.path.join(temp_dir, f"temp_title_{filename}.png")
        temp_vname = os.path.join(temp_dir, f"temp_vname_{filename}.png")

        intro_clip = None
        final_intro = None

        try:
            # Prepare Text
            raw_name = os.path.splitext(filename)[0]
            video_name_text = raw_name.replace("_", " ").title()


            # <--- ADD THIS --->
            # Wrap text if it exceeds 20 characters (adjust 'width' as desired)
            video_name_text = textwrap.fill(video_name_text, width=50)
            # <---------------->

            make_text_image(name, 35, 'yellow', temp_name, FONT_GILROY_REGULAR)
            make_text_image(title, 35, 'yellow', temp_title, FONT_GILROY_REGULAR)
            make_text_image(video_name_text, 40, 'white', temp_vname, FONT_GILROY_BOLD)

            # Base Intro
            intro_clip = VideoFileClip(intro_video_path)


            # Circular Profile
            with Image.open(profile_path).convert("RGBA") as p_img:
                size = (min(p_img.size), min(p_img.size))
                mask = Image.new("L", size, 0)
                draw = ImageDraw.Draw(mask)
                draw.ellipse((0, 0) + size, fill=255)
                output_img = ImageOps.fit(p_img, size, centering=(0.5, 0.5))
                output_img.putalpha(mask)
                output_img.save(temp_circular)

            # Create MoviePy Clips
            profile_clip = ImageClip(temp_circular).set_duration(intro_clip.duration).resize(height=intro_clip.h * 0.5)
            name_clip = ImageClip(temp_name).set_duration(intro_clip.duration)
            title_clip = ImageClip(temp_title).set_duration(intro_clip.duration)
            vname_clip = ImageClip(temp_vname).set_duration(intro_clip.duration)



            # Positioning
            margin_h = 150
            
            # Profile: Right side, vertically centered
            p_x = intro_clip.w - profile_clip.w - margin_h
            p_y = (intro_clip.h - profile_clip.h) / 2
            profile_final = profile_clip.set_position((p_x, p_y))

            # Text: Left side
            vn_x = margin_h
            vn_y = 650
            vname_final = vname_clip.set_position((vn_x, vn_y))

            n_x = margin_h
            n_y = vn_y + vname_clip.h + 10
            name_final = name_clip.set_position((n_x, n_y))

            t_x = margin_h
            t_y = n_y + name_clip.h + 10
            title_final = title_clip.set_position((t_x, t_y))

            # Composite
            final_intro = CompositeVideoClip([
                intro_clip, profile_final, vname_final, name_final, title_final
            ])

            final_intro.write_videofile(
                target_intro_path, codec="libx264", audio_codec="aac", fps=30,
                threads=4, preset="fast", verbose=False, logger=None,
                ffmpeg_params=["-pix_fmt", "yuv420p"]
            )

        except Exception as e:
            print(f"Error creating intro for {filename}: {e}")
        finally:
            if intro_clip: intro_clip.close()
            if final_intro: final_intro.close()
            # Clean temps
            for tp in [temp_circular, temp_name, temp_title, temp_vname]:
                if os.path.exists(tp): os.remove(tp)
    
    return True



def stitch_backgrounds(source_dir, output_dir, config_data, temp_dir):
    """
    Overlays the source video onto a background image using FFmpeg.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    bg_path = config_data.get("files", {}).get("background_picture")
    if not bg_path or not os.path.exists(bg_path):
        print("Background image missing.")
        return False

    # Pre-resize background to 1920x1080
    temp_bg_path = os.path.join(temp_dir, "resized_bg.png")
    try:
        img = Image.open(bg_path)
        img_resized = img.resize((1920, 1080), Image.Resampling.LANCZOS)
        img_resized.save(temp_bg_path)
    except Exception as e:
        print(f"Error resizing background: {e}")
        return False

    video_files = [f for f in os.listdir(source_dir) if f.endswith(('.mp4', '.avi', '.mov'))]

    for filename in video_files:
        print(f"Stitching background for: {filename}")
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(output_dir, filename)

        # --- THE FIX IS IN THE filter_complex LINE BELOW ---
        # We added 'setpts=PTS-STARTPTS' to the [1:v] input.
        # This forces the video overlay to start at time 0.
        
        cmd = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-loop', '1', '-i', temp_bg_path,
            '-i', source_path,
            '-filter_complex', '[1:v]setpts=PTS-STARTPTS,scale=1650:-1,fps=30[vid];[0:v][vid]overlay=(W-w)/2:(H-h)/2:shortest=1[vout]',
            '-map', '[vout]', '-map', '1:a',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-c:a', 'aac', '-pix_fmt', 'yuv420p',
            target_path
        ]
        subprocess.run(cmd)

    return True

def get_stream_info(path):
    """
    Extracts detailed video and audio metadata using ffmpeg-python.
    """
    try:
        probe = ffmpeg.probe(path)
        video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
        audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

        if not video_stream: 
            return None

        # Calculate FPS
        avg_frame_rate = video_stream.get('avg_frame_rate', '30/1')
        num, den = map(int, avg_frame_rate.split('/'))
        fps = num / den if den > 0 else 0

        # Audio details defaults
        audio_rate = int(audio_stream['sample_rate']) if audio_stream else 44100
        audio_channels = int(audio_stream['channels']) if audio_stream else 2
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
    except ffmpeg.Error as e:
        print(f"Error reading metadata for {path}: {e.stderr}")
        return None
    except Exception as e:
        print(f"General error reading {path}: {e}")
        return None

def concat_final_videos(intro_dir, stitched_dir, output_dir, temp_dir):
    """
    Concatenates the generated intro with the stitched video.
    Forces the Intro to match the Stitched video's encoding exactly before concatenating.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    intro_files = [f for f in os.listdir(intro_dir) if f.endswith(('.mp4', '.mov', '.avi'))]
    
    for filename in intro_files:
        intro_path = os.path.join(intro_dir, filename)
        stitched_path = os.path.join(stitched_dir, filename)
        final_path = os.path.join(output_dir, filename)

        if not os.path.exists(stitched_path):
            continue

        print(f"Processing Final Concatenation: {filename}")
        
        # 1. ANALYZE METADATA
        v1 = get_stream_info(intro_path)    # Intro
        v2 = get_stream_info(stitched_path) # Stitched (Master)
        
        if not v1 or not v2: 
            print(f"Skipping {filename}: Metadata error.")
            continue

        print(f"   Metadata: Intro({v1['width']}x{v1['height']} {v1['fps']:.2f}fps) | Main({v2['width']}x{v2['height']} {v2['fps']:.2f}fps)")

        # 2. CHECK & NORMALIZE
        # We check resolution, FPS (with tolerance), codec, and audio settings
        properties_match = (
            v1['width'] == v2['width'] and
            v1['height'] == v2['height'] and
            abs(v1['fps'] - v2['fps']) < 0.1 and
            v1['codec'] == v2['codec'] and
            v1['audio_rate'] == v2['audio_rate'] and
            v1['audio_channels'] == v2['audio_channels']
        )

        video1_ready_path = intro_path
        temp_normalized_intro = os.path.join(temp_dir, f"norm_{filename}")

        if not properties_match:
            print(f"   ⚠️ Mismatch detected. Normalizing Intro to match Main video...")
            
            # Map codec names to FFmpeg encoder names
            codec_map = {'h264': 'libx264', 'hevc': 'libx265', 'vp9': 'libvpx-vp9'}
            target_encoder = codec_map.get(v2['codec'], 'libx264')

            cmd_norm = [
                'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
                '-i', intro_path,
                '-vf', f"scale={v2['width']}:{v2['height']}",
                '-r', str(v2['fps']),             # Force FPS
                '-c:v', target_encoder,           # Match Codec
                '-ar', str(v2['audio_rate']),     # Match Audio Rate
                '-ac', str(v2['audio_channels']), # Match Audio Channels
                '-c:a', 'aac',                    # AAC is generally safe for container
                '-strict', 'experimental',
                temp_normalized_intro
            ]
            subprocess.run(cmd_norm)
            video1_ready_path = temp_normalized_intro
        else:
            print(f"   ✅ Format matches. No re-encoding needed.")

        # 3. CONCAT
        list_file = os.path.join(temp_dir, f"concat_{filename}.txt")
        with open(list_file, "w") as f:
            f.write(f"file '{video1_ready_path}'\n")
            f.write(f"file '{stitched_path}'\n")

        # Use stream copy (-c copy) because we ensured formats match above
        cmd_concat = [
            'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
            '-f', 'concat', '-safe', '0', '-i', list_file,
            '-c:v', 'copy', '-c:a', 'aac', final_path
        ]
        subprocess.run(cmd_concat)
        print(f"   🎉 Saved: {filename}")

        # Cleanup temps for this file
        if os.path.exists(temp_normalized_intro): os.remove(temp_normalized_intro)
        if os.path.exists(list_file): os.remove(list_file)

    return True

def run_ui_pipeline(raw_videos_dir, config_path, base_output_dir):
    """Orchestrator function called by API."""
    
    # Setup sub-folders
    intro_output_dir = os.path.join(base_output_dir, "intro_templates")
    stitched_output_dir = os.path.join(base_output_dir, "stitched_vids")
    final_output_dir = os.path.join(base_output_dir, "final_branded_videos")
    temp_dir = os.path.join(base_output_dir, "temp_ui_processing")
    
    if not os.path.exists(temp_dir): os.makedirs(temp_dir)

    # Load Config
    with open(config_path, 'r') as f:
        config_data = json.load(f)

    print("--- 1. Generating Intros ---")
    generate_intros(raw_videos_dir, intro_output_dir, config_data, temp_dir)

    print("--- 2. Stitching Backgrounds ---")
    stitch_backgrounds(raw_videos_dir, stitched_output_dir, config_data, temp_dir)

    print("--- 3. Final Concatenation ---")
    concat_final_videos(intro_output_dir, stitched_output_dir, final_output_dir, temp_dir)

    # Global cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    return final_output_dir