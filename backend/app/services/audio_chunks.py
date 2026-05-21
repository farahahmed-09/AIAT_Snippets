"""Chunk a long video/audio file into Whisper-sized slices.

ffmpeg's `segment` muxer cuts straight into N files in a single
invocation, no per-chunk re-encode. We downmix to 16 kHz mono mp3 at
32 kbps because:

  - Whisper resamples to 16 kHz mono internally, so we drop redundant
    samples up-front and shrink the upload by ~10×.
  - Each ~10-min chunk is roughly 2-3 MB — well under Whisper's 25 MB
    per-request ceiling, even with verbose-json overhead.

Strategy is time-based (not silence-based) — fast and good enough for
lectures where the LLM segmenter downstream handles "the cut landed
mid-sentence" gracefully. Silence-based chunking can come later if we
see drift across boundaries.
"""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

CHUNK_SECONDS = 600  # 10 minutes per chunk.


@dataclass(frozen=True)
class AudioChunk:
    path: Path
    start_second: float


def split_audio(source_path: str | Path, dest_dir: str | Path) -> list[AudioChunk]:
    """Demux + split `source_path` into chunked mp3s under `dest_dir`.

    Returns one `AudioChunk` per chunk in order. The chunks live as long
    as the caller keeps `dest_dir` around — wrap in a TemporaryDirectory
    upstream so they get cleaned up when the pipeline finishes.
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

    chunks = sorted(out.glob("chunk_*.mp3"))
    return [
        AudioChunk(path=p, start_second=i * CHUNK_SECONDS)
        for i, p in enumerate(chunks)
    ]
