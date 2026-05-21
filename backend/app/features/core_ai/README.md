# core_ai

The AI pieces from the legacy `old/src/` tree, parked here so we can port
them into the new architecture without keeping a `from old.*` import path.
These files are **not wired into the pipeline yet** — porting + cleanup
happens incrementally.

## Files

| File | Origin | Notes |
|------|--------|-------|
| `snippets_generation_agent.py` | `old/src/core/Agent_snippets_generation.py` | LLM agent that picks snippets from a transcript |
| `agent_service.py` | `old/src/app/services/agent_service.py` | Service wrapper around the agent; pre-refactor it touched both DB and LLM |
| `transcribe_core.py` | `old/src/core/transcribe.py` | Low-level transcription |
| `transcription_service.py` | `old/src/app/services/transcription_service.py` | Service wrapper around transcription |

## Porting target

The new pipeline expects these contracts:

- `app/services/transcribe.py::transcribe(source_path) -> Transcript`
- `app/services/segment.py::segment(transcript) -> list[ProposedSnippet]`

Move logic out of the files in this folder into those modules. Keep one
LLM call site per concern; route LLM traffic through `backend/ai_core/`
(submodule) once its API is finalised.

## Conventions

- Keep new modules under 500 lines.
- Pure functions where possible; side-effects (DB, storage) live in the
  service layer of `app/services/`, not here.
- Each public function should be testable without spinning up Celery —
  pass dependencies explicitly.
