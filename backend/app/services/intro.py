"""Brand the intro video with speaker + video-title overlays.

Mirrors the layout that the old `video_service.generate_intros` produced:

    [intro video]
        ├ right side, vertically centered, ~50% height: circular profile
        ├ left x=150, y=650:           Video title  (Gilroy-Bold,    40px, white)
        ├ left x=150, below title:     Speaker name (Gilroy-Regular, 35px, yellow)
        └ left x=150, below name:      Speaker title(Gilroy-Regular, 35px, yellow)

Implementation is PIL for the rasterised assets (multi-line text PNGs +
the circular profile PNG) and ffmpeg `overlay` for the final composite,
so we don't pull moviepy into the image just for this.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageOps


_FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"
_FONT_BOLD = _FONT_DIR / "Gilroy-Bold.ttf"
_FONT_REGULAR = _FONT_DIR / "Gilroy-Regular.ttf"

# Coordinates from the legacy layout. The old composite assumed a
# 1920x1080 intro; we honour that until the design says otherwise.
_LEFT_MARGIN = 150
_RIGHT_MARGIN = 150
_TITLE_Y = 650
_LINE_GAP = 10
_PROFILE_HEIGHT_RATIO = 0.5
_WRAP_WIDTH = 50


@dataclass(frozen=True)
class IntroBranding:
    speaker_name: Optional[str]
    speaker_title: Optional[str]
    video_title: Optional[str]
    profile_image_path: Optional[str]


def build_branded_intro(
    intro_video_path: str | Path,
    branding: IntroBranding,
    *,
    workdir: str | Path,
    output_path: str | Path,
) -> Path:
    """Composite `branding` onto `intro_video_path` → `output_path`.

    Returns the output path. Falls back to a straight copy of the intro
    when fonts/profile data is missing — the caller never has to second-
    guess "did the brand step run?", they get a valid intro either way.
    """
    intro_video_path = Path(intro_video_path)
    workdir = Path(workdir)
    output_path = Path(output_path)
    workdir.mkdir(parents=True, exist_ok=True)

    if not _FONT_BOLD.exists() or not _FONT_REGULAR.exists():
        shutil.copyfile(intro_video_path, output_path)
        return output_path

    width, height = _probe_video_dims(intro_video_path)
    text_assets = _render_text_pngs(branding, workdir)
    profile_asset = _render_profile_png(
        branding.profile_image_path, target_size=int(height * _PROFILE_HEIGHT_RATIO),
        workdir=workdir,
    )

    if not text_assets and not profile_asset:
        shutil.copyfile(intro_video_path, output_path)
        return output_path

    _run_overlay(
        intro_video_path,
        text_assets,
        profile_asset,
        canvas=(width, height),
        output_path=output_path,
    )
    return output_path


# ───────────────────────── PIL helpers ─────────────────────────


@dataclass(frozen=True)
class _TextAsset:
    path: Path
    width: int
    height: int


def _render_text_pngs(branding: IntroBranding, workdir: Path) -> list[_TextAsset]:
    """Render up to three transparent PNGs (title / name / role) stacked
    in the order they should appear top-to-bottom. Returns an empty list
    when there is nothing to draw."""
    panels: list[tuple[str, str, str, int]] = []
    if branding.video_title:
        wrapped = textwrap.fill(
            branding.video_title.replace("_", " ").replace("-", " ").title(),
            width=_WRAP_WIDTH,
        )
        panels.append((wrapped, str(_FONT_BOLD), "white", 40))
    if branding.speaker_name:
        panels.append((branding.speaker_name, str(_FONT_REGULAR), "yellow", 35))
    if branding.speaker_title:
        panels.append((branding.speaker_title, str(_FONT_REGULAR), "yellow", 35))

    assets: list[_TextAsset] = []
    for idx, (text, font_path, color, size) in enumerate(panels):
        out = workdir / f"intro_text_{idx}.png"
        asset = _draw_multiline(text, font_path, color, size, out)
        assets.append(asset)
    return assets


def _draw_multiline(
    text: str, font_path: str, color: str, size: int, out_path: Path
) -> _TextAsset:
    font = ImageFont.truetype(font_path, size)
    lines = text.split("\n")
    line_heights: list[int] = []
    max_w = 0
    for line in lines:
        bbox = font.getbbox(line)
        line_heights.append(bbox[3] - bbox[1])
        max_w = max(max_w, bbox[2] - bbox[0])
    line_gap = 4
    total_h = sum(line_heights) + line_gap * (len(lines) - 1)
    img = Image.new("RGBA", (max_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    y = 0
    for line, h in zip(lines, line_heights):
        bbox = font.getbbox(line)
        draw.text((-bbox[0], y - bbox[1]), line, fill=color, font=font)
        y += h + line_gap
    img.save(out_path)
    return _TextAsset(path=out_path, width=max_w, height=total_h)


def _render_profile_png(
    profile_image_path: Optional[str], target_size: int, workdir: Path
) -> Optional[_TextAsset]:
    if not profile_image_path or not Path(profile_image_path).exists():
        return None
    out = workdir / "intro_profile.png"
    with Image.open(profile_image_path).convert("RGBA") as src:
        side = min(src.size + (target_size, target_size))
        side = target_size  # final circle is exactly target_size
        mask = Image.new("L", (side, side), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, side, side), fill=255)
        fitted = ImageOps.fit(src, (side, side), centering=(0.5, 0.5))
        fitted.putalpha(mask)
        fitted.save(out)
    return _TextAsset(path=out, width=side, height=side)


# ───────────────────────── ffmpeg helpers ─────────────────────────


def _probe_video_dims(path: Path) -> tuple[int, int]:
    """Return (width, height). Falls back to 1920x1080 if ffprobe is
    unavailable or the stream lacks dimensions."""
    if shutil.which("ffprobe") is None:
        return 1920, 1080
    try:
        raw = subprocess.check_output(
            [
                "ffprobe",
                "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "json",
                str(path),
            ],
        )
        data = json.loads(raw)
        stream = (data.get("streams") or [{}])[0]
        return int(stream.get("width", 1920)), int(stream.get("height", 1080))
    except Exception:
        return 1920, 1080


def _run_overlay(
    intro_video_path: Path,
    text_assets: list[_TextAsset],
    profile_asset: Optional[_TextAsset],
    *,
    canvas: tuple[int, int],
    output_path: Path,
) -> None:
    width, height = canvas
    inputs: list[str] = [str(intro_video_path)]
    for a in text_assets:
        inputs.append(str(a.path))
    if profile_asset:
        inputs.append(str(profile_asset.path))

    filter_steps: list[str] = []
    current_label = "0:v"

    # Stack text panels vertically starting at (_LEFT_MARGIN, _TITLE_Y).
    cursor_y = _TITLE_Y
    for i, asset in enumerate(text_assets, start=1):
        next_label = f"vt{i}"
        filter_steps.append(
            f"[{current_label}][{i}:v]overlay={_LEFT_MARGIN}:{cursor_y}[{next_label}]"
        )
        current_label = next_label
        cursor_y += asset.height + _LINE_GAP

    if profile_asset:
        profile_input_index = len(inputs) - 1
        p_x = width - profile_asset.width - _RIGHT_MARGIN
        p_y = (height - profile_asset.height) // 2
        next_label = "vp"
        filter_steps.append(
            f"[{current_label}][{profile_input_index}:v]overlay={p_x}:{p_y}[{next_label}]"
        )
        current_label = next_label

    args = ["ffmpeg", "-y", "-loglevel", "error"]
    for inp in inputs:
        args += ["-i", inp]
    args += [
        "-filter_complex", ";".join(filter_steps),
        "-map", f"[{current_label}]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]
    subprocess.run(args, check=True)
