"""Render one branded snippet with ffmpeg.

Composition (in order):

    [branded intro = intro video + speaker overlays + circular profile]
    ⊕
    [source trimmed to (start, end)]

`services.intro.build_branded_intro` produces the branded intro via
PIL-rendered PNGs and ffmpeg `overlay`; this module trims the source
slice and concats. When there is no intro, we just emit the trimmed
slice.

Pure subprocess; no ffmpeg-python dep.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.services.intro import IntroBranding, build_branded_intro


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
    video_title: str | None = None


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
        branded_intro = workdir / "_intro_branded.mp4"
        build_branded_intro(
            inputs.intro_video_path,
            IntroBranding(
                speaker_name=inputs.speaker_name,
                speaker_title=inputs.speaker_title,
                video_title=inputs.video_title,
                profile_image_path=inputs.speaker_image_path,
            ),
            workdir=workdir,
            output_path=branded_intro,
        )
        _concat(branded_intro, slice_path, Path(output_path))
        slice_path.unlink(missing_ok=True)
        branded_intro.unlink(missing_ok=True)
    else:
        shutil.move(slice_path, output_path)

    return output_path


# ───────────────────────── ffmpeg invocations ─────────────────────────


def _extract_slice(inputs: RenderInputs, dest: Path) -> None:
    """Trim the source to [start, end] precisely.

    `-ss` *after* `-i` is the accurate seek — re-encodes from the
    requested frame, not from the prior keyframe.
    """
    args = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", inputs.source_video_path,
        "-ss", str(inputs.start_second),
        "-to", str(inputs.end_second),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(dest),
    ]
    subprocess.run(args, check=True)


def _concat(intro: Path, slice_: Path, dest: Path) -> None:
    """Re-encode-concat the branded intro and the trimmed slice.

    `concat` filter (not the demuxer) so we don't need matched codecs
    or timebases. `[*:a:0?]` makes audio optional on each input, so a
    silent intro doesn't bring the whole filter graph down.
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
