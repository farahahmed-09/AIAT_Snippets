"""Render one branded snippet with ffmpeg.

Composition (in order):

    [optional intro video] ⊕ [source trimmed to (start, end) with optional
                              speaker name/title text overlay]

Re-encodes through libx264 + AAC so the concat works across mismatched
codecs and so the trim cuts on exact frames (not the keyframe nearest
the requested timestamp).

Pure subprocess; no ffmpeg-python dep. Keeps the image lean. Image
overlays (speaker avatar, background card) come in a follow-up — they
need extra positioning math we'll write once the visual spec is final.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


@dataclass(frozen=True)
class RenderInputs:
    source_video_path: str
    start_second: int
    end_second: int
    intro_video_path: str | None = None
    speaker_name: str | None = None
    speaker_title: str | None = None
    speaker_image_path: str | None = None
    background_image_path: str | None = None


def render_snippet(inputs: RenderInputs, *, output_path: str) -> str:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not installed in this image")
    if inputs.end_second <= inputs.start_second:
        raise ValueError("end_second must be > start_second")

    workdir = Path(output_path).parent
    workdir.mkdir(parents=True, exist_ok=True)
    slice_path = workdir / "_slice.mp4"

    _extract_slice(inputs, slice_path)

    if inputs.intro_video_path:
        _concat_intro(Path(inputs.intro_video_path), slice_path, Path(output_path))
        slice_path.unlink(missing_ok=True)
    else:
        shutil.move(slice_path, output_path)

    return output_path


# ───────────────────────── ffmpeg invocations ─────────────────────────


def _extract_slice(inputs: RenderInputs, dest: Path) -> None:
    """Trim the source to [start, end] and stamp the speaker overlay.

    `-ss` before `-i` is the fast seek; we follow with `-to` which
    re-encodes from the keyframe nearest start through the exact end,
    so cuts land on the requested frame.
    """
    vf = _drawtext_filter(inputs.speaker_name, inputs.speaker_title)
    args = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-ss", str(inputs.start_second),
        "-to", str(inputs.end_second),
        "-i", inputs.source_video_path,
    ]
    if vf:
        args += ["-vf", vf]
    args += [
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(dest),
    ]
    subprocess.run(args, check=True)


def _concat_intro(intro: Path, slice_: Path, dest: Path) -> None:
    """Re-encode-concat the intro and the trimmed slice into `dest`.

    `concat` filter (not the demuxer) so we don't need matched codecs
    or timebases. Slower than `-c copy` but robust to mixed sources.
    """
    args = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(intro),
        "-i", str(slice_),
        "-filter_complex",
        "[0:v:0][0:a:0?][1:v:0][1:a:0?]concat=n=2:v=1:a=1[v][a]",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(dest),
    ]
    subprocess.run(args, check=True)


def _drawtext_filter(name: str | None, title: str | None) -> str | None:
    """Build a `drawtext` filter that places speaker name + title in the
    bottom-left corner. Returns None when there's nothing to draw."""
    if not name and not title:
        return None
    if not Path(_FONT).exists():
        # No font installed — fall back to no overlay rather than failing
        # the whole render. Dockerfile installs fonts-dejavu-core to fix.
        return None

    lines: list[str] = []
    if name:
        lines.append(
            f"drawtext=fontfile={_FONT}:text='{_escape(name)}'"
            f":x=48:y=h-tw-56:fontsize=34:fontcolor=white"
            f":box=1:boxcolor=black@0.45:boxborderw=12"
        )
    if title:
        lines.append(
            f"drawtext=fontfile={_FONT}:text='{_escape(title)}'"
            f":x=48:y=h-th-24:fontsize=22:fontcolor=white@0.85"
            f":box=1:boxcolor=black@0.35:boxborderw=10"
        )
    return ",".join(lines)


def _escape(text: str) -> str:
    """Escape characters that drawtext treats as control chars."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace("%", r"\%")
    )
