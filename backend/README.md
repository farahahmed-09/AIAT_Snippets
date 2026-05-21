# SmartCut AI — backend

FastAPI + Celery + Supabase. **Template scaffold** — the legacy backend lives
under [../old/src/](../old/src/) and should be ported in incrementally.

## Stack

| Concern        | Choice                                |
|----------------|---------------------------------------|
| Framework      | FastAPI (latest)                      |
| Server         | uvicorn (standard)                    |
| Settings       | pydantic-settings (env-driven)        |
| Auth           | Supabase JWT (HS256) verified server-side |
| Database       | Supabase Postgres via `supabase-py`   |
| Storage        | Supabase Storage (`snippets` bucket)  |
| Workers        | Celery + Redis                        |
| Logging        | structlog (JSON)                      |
| Tests          | pytest + httpx                        |

Python ≥ 3.12.

## Layout

```
app/
├── main.py                  # FastAPI app factory + middleware + router include
├── api/
│   ├── deps.py              # CurrentUserDep
│   └── v1/
│       ├── router.py
│       └── endpoints/
│           ├── health.py
│           ├── sessions.py  # TODO: port from old/src/app/api/routes/
│           └── snippets.py  # TODO: port from old/src/app/api/routes/
├── core/
│   ├── config.py            # Settings(BaseSettings) — env-driven
│   ├── security.py          # decode_supabase_jwt + get_current_user
│   └── logging.py           # structlog JSON
├── db/
│   └── supabase.py          # admin + per-user client factories
├── models/                  # domain models (if needed beyond schemas)
├── schemas/
│   ├── session.py
│   └── snippet.py
├── services/                # TODO: port drive/transcribe/agent/video/storage
└── workers/
    ├── celery_app.py
    └── tasks.py             # TODO: port from old/src/app/workers/tasks.py
tests/
└── test_health.py
```

## Getting started

```bash
cp .env.example .env
# fill in SUPABASE_* and SUPABASE_JWT_SECRET

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

uvicorn app.main:app --reload
```

Visit `http://localhost:8000/docs` for the OpenAPI UI.

Run the worker in a second terminal:

```bash
celery -A app.workers.celery_app worker --loglevel=info
```

Tests:

```bash
pytest
```

## Auth

The `get_current_user` dependency in [app/core/security.py](app/core/security.py)
verifies the Supabase JWT (HS256) using `SUPABASE_JWT_SECRET` and returns a
`CurrentUser(id, email)`. Use the `CurrentUserDep` alias in
[app/api/deps.py](app/api/deps.py) on any protected endpoint:

```python
@router.get("/me")
def me(user: CurrentUserDep) -> dict[str, str | None]:
    return {"id": user.id, "email": user.email}
```

## Two Supabase clients

- **admin** — `get_supabase_admin()` — service-role key, bypasses RLS. Use
  for cross-tenant background work (workers) and anywhere you've already
  authorised the caller at the API layer.
- **per-user** — `get_supabase_user(access_token)` — anon key + the caller's
  JWT, so PostgREST applies the RLS policies defined in
  [../supabase/migrations/20260521000004_projects.sql](../supabase/migrations/20260521000004_projects.sql) naturally.

## Porting from `old/src/`

The route handlers, services, and Celery tasks in `old/src/app/` and
`old/src/core/` are the source of behaviour. Port one route at a time:
copy the handler, swap the SQLAlchemy/legacy access for the Supabase
clients above, validate with pytest, then delete the corresponding file
from `old/` once the new version is wired in.
