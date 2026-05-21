"""Transcribe a long video/audio file via ai_core, chunked.

Whisper has a 25 MB request ceiling and degrades on multi-hour audio.
The flow here is:

  1. ffmpeg-split the source into ~10 min mono mp3 chunks (see
     `services.audio_chunks`).
  2. Hit `audio.transcribe_segments` per chunk — Whisper-1 verbose_json
     gives us segment-level timestamps inside the chunk.
  3. Shift each chunk's timestamps by the chunk's start offset and
     concatenate so the caller sees a single global timeline.

Failures on individual chunks abort the whole job (a hole in the middle
would silently bias every downstream snippet). Chunk files live under a
TemporaryDirectory and are cleaned up automatically.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass

from app.services.ai import run_ai_task
from app.services.audio_chunks import AudioChunk, split_audio


@dataclass(frozen=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Transcript:
    full_text: str
    segments: list[TranscriptSegment]


def transcribe(source_video_path: str) -> Transcript:
    with tempfile.TemporaryDirectory(prefix="snippets-chunks-") as tmp:
        chunks = split_audio(source_video_path, tmp)
        if not chunks:
            return Transcript(full_text="", segments=[])

        all_segments: list[TranscriptSegment] = []
        for chunk in chunks:
            all_segments.extend(_transcribe_chunk(chunk))

    all_segments.sort(key=lambda s: s.start)
    full_text = " ".join(s.text for s in all_segments).strip()
    return Transcript(full_text=full_text, segments=all_segments)


def _transcribe_chunk(chunk: AudioChunk) -> list[TranscriptSegment]:
    out = run_ai_task(
        "audio.transcribe_segments",
        {"audio_path": str(chunk.path)},
    )
    if out.status != "success":
        message = out.error.message if out.error else "unknown transcription failure"
        raise RuntimeError(
            f"Transcription failed on chunk @ {chunk.start_second:.0f}s: {message}"
        )

    offset = chunk.start_second
    return [
        TranscriptSegment(
            start=float(s["start"]) + offset,
            end=float(s["end"]) + offset,
            text=str(s["text"]).strip(),
        )
        for s in out.data.get("segments") or []
        if "start" in s and "end" in s and "text" in s
    ]
