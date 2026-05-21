# SmartCut AI

Long lecture/webinar → AI-segmented → branded short clips.

This repo holds the **refactor** of the original SmartCut app. The legacy
Vite/React frontend and pre-refactor FastAPI backend live under
[old/](old/) (gitignored on disk) and are being ported into the new
templates incrementally.

## Layout

```
.
├── frontend/   Next.js 16 (App Router) + Tailwind 4 + shadcn/ui + Supabase Auth
├── backend/    FastAPI 0.136+ + Celery + Supabase + structlog
├── db/         Supabase SQL bootstrap (run once per project)
├── old/        Legacy code, kept for porting reference (gitignored)
└── docker-compose.yml
```

## Quick start with Docker Compose

The compose file boots five services: `redis`, `backend`, `worker`, `beat`,
`frontend`.

```bash
# 1. Set up Supabase: run db/01_schema.sql, db/02_storage.sql,
#    db/03_auth.sql, db/04_projects.sql in the SQL editor.

# 2. Create env files
cp .env.example .env                       # NEXT_PUBLIC_* baked into the Next build
cp backend/.env.example backend/.env       # FastAPI + Celery runtime env
# Fill in the SUPABASE_* values in both.

# 3. Boot everything
docker compose up --build
```

Then:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000/api/v1>
- API docs: <http://localhost:8000/docs>

Useful one-offs:

```bash
docker compose logs -f worker          # tail Celery worker output
docker compose run --rm backend pytest # run tests inside the backend image
docker compose down -v                 # stop and wipe redis + beat volumes
```

## Running without Docker

Each app has its own README with native-run instructions:

- [frontend/README.md](frontend/README.md) — needs Node ≥ 20.9
- [backend/README.md](backend/README.md) — needs Python ≥ 3.12 + Redis

## Env layering

| File              | Read by                  | Holds                                          |
|-------------------|--------------------------|------------------------------------------------|
| `./.env`          | `docker-compose.yml`     | `NEXT_PUBLIC_*` build args for the Next image  |
| `./backend/.env`  | the FastAPI container    | `SUPABASE_*`, `SUPABASE_JWT_SECRET`, `REDIS_URL` |
| `./frontend/.env.local` | `npm run dev` outside Docker | `NEXT_PUBLIC_*` for local dev               |

`backend/.env` is marked `required: false` in compose so `docker compose
config` works in fresh checkouts — but the backend will refuse to start
until you populate it (pydantic-settings validates on import).
