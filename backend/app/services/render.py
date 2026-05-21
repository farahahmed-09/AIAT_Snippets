"""Render one branded snippet with ffmpeg.

Composition (in order):

    [branded intro = intro video + speaker overlays + circular profile]
    ⊕
    [source trimmed to (start, end)]

`services.intro.build_branded_intro` produces the branded intro via
PIL-rendered PNGs and ffmpeg `overlay`; this module trims the source
slice and concats. When there is no intro, we just emit the trimmed
slice.

Every ffmpeg invocation:
  - clamps the end second to the actual source duration (otherwise
    ffmpeg silently emits a 0-byte stream + exit 0)
  - probes the result and rejects empty / sub-second outputs so the
    caller never uploads a broken video
  - captures stderr and surfaces it in the raised RuntimeError

Pure subprocess; no ffmpeg-python dep.
"""

from __future__ import annotations

import json
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

    source_duration = _probe_duration(Path(inputs.source_video_path))
    clamped_end = min(inputs.end_second, _floor_int(source_duration))
    if clamped_end <= inputs.start_second:
        raise ValueError(
            f"start_second {inputs.start_second} is at/past source duration "
            f"{source_duration:.1f}s — nothing to render"
        )
    trimmed_inputs = (
        inputs
        if clamped_end == inputs.end_second
        else _replace(inputs, end_second=clamped_end)
    )

    workdir = Path(output_path).parent
    workdir.mkdir(parents=True, exist_ok=True)
    slice_path = workdir / "_slice.mp4"

    _extract_slice(trimmed_inputs, slice_path)

    if trimmed_inputs.intro_video_path:
        branded_intro = workdir / "_intro_branded.mp4"
        build_branded_intro(
            trimmed_inputs.intro_video_path,
            IntroBranding(
                speaker_name=trimmed_inputs.speaker_name,
                speaker_title=trimmed_inputs.speaker_title,
                video_title=trimmed_inputs.video_title,
                profile_image_path=trimmed_inputs.speaker_image_path,
            ),
            workdir=workdir,
            output_path=branded_intro,
        )
        _concat(branded_intro, slice_path, Path(output_path))
        slice_path.unlink(missing_ok=True)
        branded_intro.unlink(missing_ok=True)
    else:
        shutil.move(slice_path, output_path)

    _assert_valid_video(Path(output_path))
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
    _run(args)
    _assert_valid_video(dest)


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
    _run(args)


# ───────────────────────── helpers ─────────────────────────


def _run(args: list[str]) -> None:
    """Run a subprocess and surface stderr on failure. Without this,
    ffmpeg's error messages disappear into the void with `check=True`."""
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        cmd = " ".join(args[:3])
        raise RuntimeError(f"{cmd} failed: {result.stderr.strip()}")


def _probe_duration(path: Path) -> float:
    raw = subprocess.check_output(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(path),
        ]
    )
    data = json.loads(raw)
    duration = data.get("format", {}).get("duration")
    if duration is None:
        raise RuntimeError(f"ffprobe did not return a duration for {path}")
    return float(duration)


def _assert_valid_video(path: Path) -> None:
    """ffmpeg can produce a 0-byte mp4 with exit 0 (e.g. `-ss` past
    duration). Catch that here so we never upload garbage."""
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"ffmpeg produced empty output: {path}")
    duration = _probe_duration(path)
    if duration < 0.1:
        raise RuntimeError(
            f"ffmpeg produced a sub-100ms output ({duration:.3f}s) at {path}"
        )


def _floor_int(value: float) -> int:
    return int(value) if value >= 0 else int(value) - 1


def _replace(inputs: RenderInputs, **overrides) -> RenderInputs:
    # `dataclasses.replace` does the same; written out here to avoid the
    # extra import and keep the file under the 500-line cap.
    return RenderInputs(
        source_video_path=overrides.get("source_video_path", inputs.source_video_path),
        start_second=overrides.get("start_second", inputs.start_second),
        end_second=overrides.get("end_second", inputs.end_second),
        intro_video_path=overrides.get("intro_video_path", inputs.intro_video_path),
        speaker_name=overrides.get("speaker_name", inputs.speaker_name),
        speaker_title=overrides.get("speaker_title", inputs.speaker_title),
        speaker_image_path=overrides.get("speaker_image_path", inputs.speaker_image_path),
        background_image_path=overrides.get(
            "background_image_path", inputs.background_image_path
        ),
        video_title=overrides.get("video_title", inputs.video_title),
    )
