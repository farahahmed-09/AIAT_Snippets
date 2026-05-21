from dataclasses import dataclass


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
    """Run speech-to-text on a local video file.

    TODO: wire to the project's transcription provider. Options:
      - whisperx / faster-whisper local
      - OpenAI Whisper API
      - AssemblyAI / Deepgram
    Should return word-level (or sentence-level) timestamps so the
    segmentation stage has something to chew on.
    """
    raise NotImplementedError(
        "Transcription not wired yet — pick a provider and implement here."
    )
