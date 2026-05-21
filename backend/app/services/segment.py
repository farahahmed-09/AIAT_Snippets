from dataclasses import dataclass

from app.services.transcribe import Transcript


@dataclass(frozen=True)
class ProposedSnippet:
    name: str
    summary: str
    start_second: int
    end_second: int


def segment(transcript: Transcript, *, target_count: int = 5) -> list[ProposedSnippet]:
    """Ask an LLM to pick the best `target_count` snippets from a transcript.

    TODO: integrate with backend/ai_core (submodule). The contract:
      - input: transcript text + segment timestamps
      - output: 3–8 ProposedSnippet entries, each 30s–120s, no overlaps
      - prompt should require the model to cite which transcript segment
        each snippet is anchored to, then we map back to seconds.

    Until the ai_core read-permission lands, this raises so the worker
    parks the job in 'Failed: segmentation not wired' rather than
    silently producing empty results.
    """
    raise NotImplementedError(
        "Segmentation needs ai_core; see backend/ai_core/ once integrated."
    )
