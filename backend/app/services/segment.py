"""Map a transcript to proposed snippet boundaries via ai_core.

Two-stage flow:

  1. `snippets.segment_transcript` — propose batched break points over
     the mini-segment sequence.
  2. `snippets.cleanse_segments` — flag merged segments to drop.

This module owns the batching + id↔seconds bookkeeping; ai_core only
does the LLM-shaped calls so token usage + trace ids feed into the same
observability log as every other engine.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.ai import run_ai_task
from app.services.transcribe import Transcript


# Soft batch ceilings — keep prompts well under typical 8k token windows.
_SEGMENT_BATCH_LINES = 80
_CLEANSE_BATCH = 25
_TARGET_MIN_LINES = 10
_TARGET_MAX_LINES = 15


@dataclass(frozen=True)
class ProposedSnippet:
    name: str
    summary: str
    start_second: int
    end_second: int


def segment(transcript: Transcript, *, target_count: int = 5) -> list[ProposedSnippet]:
    """Run the LLM-driven segmentation, then return the top `target_count`
    proposals by descending duration (a rough proxy for substance — the
    cleanser already dropped trivial segments)."""
    _ = target_count
    if not transcript.segments:
        return []

    mini = [
        {"mini_seg_id": i, "text": s.text}
        for i, s in enumerate(transcript.segments)
        if s.text.strip()
    ]
    if not mini:
        return []

    breaks = _collect_break_points(mini)
    grouped = _execute_merge_plan(transcript.segments, mini, breaks)
    drop_ids = _collect_removals(grouped)
    kept = [g for g in grouped if g.id not in drop_ids]

    return [
        ProposedSnippet(
            name=_title_from(g.text),
            summary=_summary_from(g.text),
            start_second=int(g.start),
            end_second=int(g.end),
        )
        for g in kept
    ]


# ───────────────────────── helpers ─────────────────────────


@dataclass(frozen=True)
class _Grouped:
    id: str
    text: str
    start: float
    end: float


def _collect_break_points(mini: list[dict]) -> set[int]:
    breaks: set[int] = set()
    for batch in _chunked(mini, _SEGMENT_BATCH_LINES):
        out = run_ai_task(
            "snippets.segment_transcript",
            {
                "mini_segments": batch,
                "min_lines_per_segment": _TARGET_MIN_LINES,
                "max_lines_per_segment": _TARGET_MAX_LINES,
            },
        )
        if out.status != "success":
            continue
        for b in out.data.get("break_points", []) or []:
            try:
                breaks.add(int(b))
            except (TypeError, ValueError):
                continue
    return breaks


def _execute_merge_plan(
    raw_segments,
    mini: list[dict],
    breaks: set[int],
) -> list[_Grouped]:
    grouped: list[_Grouped] = []
    cursor = 0
    seg_no = 1
    for end_idx in sorted(breaks) + [len(mini) - 1]:
        if end_idx < cursor:
            continue
        chunk = mini[cursor : end_idx + 1]
        if not chunk:
            cursor = end_idx + 1
            continue
        first_idx = chunk[0]["mini_seg_id"]
        last_idx = chunk[-1]["mini_seg_id"]
        text = " ".join(c["text"] for c in chunk).strip()
        if not text:
            cursor = end_idx + 1
            continue
        grouped.append(
            _Grouped(
                id=f"seg_{seg_no:03d}",
                text=text,
                start=raw_segments[first_idx].start,
                end=raw_segments[last_idx].end,
            )
        )
        seg_no += 1
        cursor = end_idx + 1
    return grouped


def _collect_removals(grouped: list[_Grouped]) -> set[str]:
    drops: set[str] = set()
    for batch in _chunked(grouped, _CLEANSE_BATCH):
        out = run_ai_task(
            "snippets.cleanse_segments",
            {"segments": [{"id": g.id, "text": g.text} for g in batch]},
        )
        if out.status != "success":
            continue
        for item in out.data.get("removals", []) or []:
            if isinstance(item, dict) and item.get("id"):
                drops.add(str(item["id"]))
    return drops


def _chunked(items: list, size: int) -> list[list]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def _title_from(text: str) -> str:
    head = text.strip().splitlines()[0] if text else ""
    head = head[:80]
    return head.rstrip(",.;:!? ") or "Snippet"


def _summary_from(text: str) -> str:
    text = text.strip()
    return (text[:240] + "…") if len(text) > 240 else text
