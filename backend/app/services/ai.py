"""Singleton accessor for the ai_core AIFactory.

ai_core's `AIFactory` is expensive to construct (each engine builds its
own pydantic-ai Agent + httpx client at boot). One factory per worker
process is the recommended shape; callers go through `get_ai_factory()`
so we share one instance.

Under Celery's prefork pool, the first task to hit this in a given
worker process pays the cost; subsequent tasks reuse it. ai_core engines
detect event-loop changes between `asyncio.run()` invocations and
rebuild any loop-bound clients themselves, so the same factory is safe
to use across the per-task asyncio.run() boundary.
"""

from __future__ import annotations

from functools import lru_cache

from ai_core.contracts.schemas import TaskInput, TaskOutput
from ai_core.factory import AIFactory


@lru_cache(maxsize=1)
def get_ai_factory() -> AIFactory:
    return AIFactory()


def run_ai_task(task_type: str, payload: dict, *, model_name: str | None = None) -> TaskOutput:
    request = TaskInput(task_type=task_type, payload=payload, model_name=model_name)
    return get_ai_factory().run_task_sync(request)
