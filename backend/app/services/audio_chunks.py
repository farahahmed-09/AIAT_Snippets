"""Chunk a long video/audio file into Whisper-sized slices.

ffmpeg's `segment` muxer cuts straight into N files in a single
invocation, no per-chunk re-encode. We downmix to 16 kHz mono mp3 at
32 kbps because:

  - Whisper resamples to 16 kHz mono internally, so we drop redundant
    samples up-front and shrink the upload by ~10×.
  - Each ~10-min chunk is roughly 2-3 MB — well under Whisper's 25 MB
    per-request ceiling, even with verbose-json overhead.

`segment_time` is a hint, not a guarantee — ffmpeg cuts on the nearest
keyframe, so actual chunk lengths drift a few seconds. We **ffprobe
each emitted file** and accumulate the true durations into the chunk
offsets, so the downstream transcript-timestamp shift stays accurate
across boundaries (the alternative — assuming uniform CHUNK_SECONDS —
silently misaligns every chunk past the first).

Strategy is time-based (not silence-based) — fast and good enough for
lectures.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

CHUNK_SECONDS = 600  # 10 minutes per chunk (hint to ffmpeg's segmenter).


@dataclass(frozen=True)
class AudioChunk:
    path: Path
    start_second: float


def split_audio(source_path: str | Path, dest_dir: str | Path) -> list[AudioChunk]:
    """Demux + split `source_path` into chunked mp3s under `dest_dir`.

    Returns one `AudioChunk` per chunk in order, with `start_second`
    derived from cumulative real durations (probed via ffprobe), not
    the requested chunk length.
    """
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(src)

    out = Path(dest_dir)
    out.mkdir(parents=True, exist_ok=True)

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg not installed in this image")

    pattern = out / "chunk_%03d.mp3"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel", "error",
            "-i", str(src),
            "-vn",                       # drop video track
            "-ar", "16000",             # 16 kHz
            "-ac", "1",                 # mono
            "-b:a", "32k",              # 32 kbps mp3
            "-f", "segment",
            "-segment_time", str(CHUNK_SECONDS),
            "-reset_timestamps", "1",
            str(pattern),
        ],
        check=True,
    )

    files = sorted(out.glob("chunk_*.mp3"))
    chunks: list[AudioChunk] = []
    cursor = 0.0
    for p in files:
        chunks.append(AudioChunk(path=p, start_second=cursor))
        cursor += _probe_duration(p)
    return chunks


def _probe_duration(path: Path) -> float:
    """Return the file's duration in seconds. Raises if unavailable —
    silent fallback would re-introduce the offset drift this module
    exists to prevent."""
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
