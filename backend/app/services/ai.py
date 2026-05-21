"""Singleton accessor for the ai_core AIFactory + retry-wrapped task runner.

ai_core's `AIFactory` is expensive to construct (each engine builds its
own pydantic-ai Agent + httpx client at boot). One factory per worker
process is the recommended shape; callers go through `get_ai_factory()`
so we share one instance.

Under Celery's prefork pool, the first task to hit this in a given
worker process pays the cost; subsequent tasks reuse it. ai_core engines
detect event-loop changes between `asyncio.run()` invocations and
rebuild any loop-bound clients themselves, so the same factory is safe
to use across the per-task asyncio.run() boundary.

Retry: `run_ai_task` wraps the call with tenacity — 5 attempts, expo
backoff 2-60s, retrying only on the `TaskOutput.error.code` values that
indicate a transient provider problem (timeout, quota/429, unknown).
Validation / content-filter errors are NOT retried because the prompt
needs to change. The old code's 10× retry was the same idea but treated
every error as transient; the new shape is more surgical so a
hard-coded bad prompt doesn't burn 10 LLM calls before failing.
"""

from __future__ import annotations

from functools import lru_cache

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai_core.contracts.schemas import AIErrorCode, TaskInput, TaskOutput
from ai_core.factory import AIFactory


_RETRYABLE_CODES = frozenset(
    {
        AIErrorCode.PROVIDER_TIMEOUT,
        AIErrorCode.QUOTA_EXCEEDED,
        AIErrorCode.UNKNOWN_ERROR,
    }
)


class _TransientAIError(RuntimeError):
    """Raised so tenacity sees a retry signal. Carries the original
    TaskOutput so callers can fall through to the non-retry path if
    every attempt fails."""

    def __init__(self, output: TaskOutput) -> None:
        super().__init__(
            output.error.message if output.error else "transient ai_core failure"
        )
        self.output = output


@lru_cache(maxsize=1)
def get_ai_factory() -> AIFactory:
    return AIFactory()


def run_ai_task(
    task_type: str, payload: dict, *, model_name: str | None = None
) -> TaskOutput:
    request = TaskInput(task_type=task_type, payload=payload, model_name=model_name)
    try:
        return _execute_with_retry(request)
    except _TransientAIError as exc:
        # Out of retry attempts — return the last TaskOutput so the
        # caller can decide whether to escalate. Same shape as a non-
        # retryable failure.
        return exc.output


@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    retry=retry_if_exception_type(_TransientAIError),
)
def _execute_with_retry(request: TaskInput) -> TaskOutput:
    output = get_ai_factory().run_task_sync(request)
    if output.status == "success":
        return output
    if output.error and output.error.code in _RETRYABLE_CODES:
        raise _TransientAIError(output)
    return output
