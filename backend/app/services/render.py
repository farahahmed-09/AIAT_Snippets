from dataclasses import dataclass


@dataclass(frozen=True)
class RenderInputs:
    source_video_path: str
    start_second: int
    end_second: int
    intro_video_path: str | None
    speaker_name: str | None
    speaker_title: str | None
    speaker_image_path: str | None
    background_image_path: str | None


def render_snippet(inputs: RenderInputs, *, output_path: str) -> str:
    """Produce a branded short clip and return the local output path.

    Composition:
      1. (Optional) intro video prepended
      2. Source slice trimmed to [start_second, end_second]
      3. Speaker name/title overlay during the slice
      4. Background image as the cut-away frame when relevant

    TODO: implement with ffmpeg-python or moviepy. Should be CPU-bound,
    no GPU. The worker will call this from a Celery task.
    """
    _ = inputs, output_path
    raise NotImplementedError("Rendering not wired yet — implement with ffmpeg.")
