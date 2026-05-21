# SmartCut AI

Long lecture/webinar → AI-segmented → branded short clips.

This repo holds the **refactor** of the original SmartCut app. The legacy
Vite/React frontend and pre-refactor FastAPI backend live under
[old/](old/) (gitignored on disk) as a porting reference.

## Layout

```
.
├── frontend/   Next.js 16 (App Router) + Tailwind 4 + shadcn/ui + Supabase Auth
├── backend/    FastAPI 0.136+ + Celery + Supabase + structlog
│   └── ai_core/         git submodule — ai_core LLM gateway (pydantic-ai)
├── supabase/   Supabase CLI project — migrations live in supabase/migrations/
├── old/        Legacy code, kept for porting reference (gitignored)
└── docker-compose.yml
```

## Prerequisites

1. **A Supabase project.** Free tier is fine. Note the project URL.
2. **A LiteLLM proxy** reachable from the backend container. ai_core
   routes every chat + audio call through it; without a valid
   `LITELLM_API_KEY` the `AIFactory()` constructor fails at first task.
3. **Docker + Docker Compose** (the supported dev path).

## Quick start

```bash
# 1. Clone with the ai_core submodule.
git clone --recurse-submodules <repo-url> && cd Snippets
# (already cloned? `git submodule update --init --recursive`)

# 2. Apply the SQL schema to your Supabase project.
supabase link --project-ref <project-ref>
supabase db push
# (see supabase/README.md for the 5 migrations this runs)

# 3. Configure the auth redirect URLs in the Supabase dashboard:
#    Auth → URL Configuration → Site URL = http://localhost:3001
#    Auth → URL Configuration → Redirect URLs = http://localhost:3001/**
#    Auth → Providers → Email → Confirm email = OFF (for local dev)

# 4. Fill in env files.
cp .env.example .env                       # NEXT_PUBLIC_* — baked into the Next image
cp backend/.env.example backend/.env       # FastAPI + Celery + ai_core runtime
# Required keys (see Env section below).

# 5. Boot everything.
docker compose up --build
```

URLs:

- **Frontend**: <http://localhost:3001>
- **Backend API**: <http://localhost:8000/api/v1>
- **API docs**: <http://localhost:8000/docs>

The frontend is mapped to host port **3001** (not 3000) because VS Code's
remote tunnel binds 3000 on many setups. The compose default is fine to
leave as-is.

Useful one-offs:

```bash
docker compose logs -f worker          # tail Celery worker output
docker compose run --rm backend pytest # run tests inside the backend image
docker compose down                    # stop containers (keeps volumes)
docker compose down -v                 # stop + wipe redis + beat volumes
```

## Env layering

| File                    | Read by                              | Holds                                                                     |
|-------------------------|--------------------------------------|---------------------------------------------------------------------------|
| `./.env`                | `docker-compose.yml`                 | `NEXT_PUBLIC_*` build args for the Next image                             |
| `./backend/.env`        | the FastAPI + worker + beat containers | `SUPABASE_*`, `REDIS_URL`, `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `DEFAULT_MODEL` |
| `./frontend/.env.local` | `npm run dev` outside Docker         | `NEXT_PUBLIC_*` for local dev                                             |

`backend/.env` is marked `required: false` in compose so `docker compose
config` works in fresh checkouts — but the backend will refuse to start
until you populate `SUPABASE_*` and `LITELLM_API_KEY` (pydantic-settings
validates on first task).

### Required `backend/.env` keys

| Key | Where to get it |
|-----|-----------------|
| `SUPABASE_URL` | Supabase dashboard → Project Settings → API |
| `SUPABASE_PUBLISHABLE_KEY` | API Keys (`sb_publishable_*`) |
| `SUPABASE_SECRET_KEY` | API Keys (`sb_secret_*`) |
| `LITELLM_BASE_URL` | Your LiteLLM gateway, e.g. `https://llm.acme.com` |
| `LITELLM_API_KEY` | Issued by your LiteLLM proxy |
| `DEFAULT_MODEL` | Provider-prefixed LiteLLM model, e.g. `openai/gpt-4o-mini` |

### Required `./.env` keys (build-time for the Next image)

| Key |
|-----|
| `NEXT_PUBLIC_SUPABASE_URL` |
| `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY` |
| `NEXT_PUBLIC_API_URL` (defaults to `http://localhost:8000/api/v1`) |

## ai_core submodule

`backend/ai_core/` is a git submodule. After cloning:

```bash
git submodule update --init --recursive
```

If you change anything under `backend/ai_core/`, those edits are
**not** captured by parent-repo commits — you commit them in the
submodule first, push it upstream, then bump the parent's submodule
pointer:

```bash
cd backend/ai_core
git add -A && git commit -m "..."
git push                    # if you have access to the ai_core repo
cd ../..
git add backend/ai_core
git commit -m "chore: bump ai_core submodule"
```

A fresh checkout that skips the submodule update will fail at
`docker compose build backend` because the Dockerfile installs
`./ai_core` as a local package.

## Running without Docker

Each app has its own README with native-run instructions:

- [frontend/README.md](frontend/README.md) — needs Node ≥ 20.9
- [backend/README.md](backend/README.md) — needs Python ≥ 3.12 + Redis + ffmpeg

## Pipeline status

End-to-end flow: signup → project → session → process → snippets →
render → download.

| Stage | Backed by | Status |
|-------|-----------|--------|
| Drive download (public + OAuth) | `services/drive.py` | ✅ |
| Source caching in Supabase Storage | `services/source_cache.py` | ✅ |
| Audio chunking (ffmpeg segment-mux) | `services/audio_chunks.py` | ✅ |
| Transcription (ai_core `audio.transcribe_segments`, chunked) | `services/transcribe.py` | ✅ |
| Segmentation + cleanse (ai_core `snippets.*`) | `services/segment.py` | ✅ |
| Render: trim + branded intro (Gilroy + circular profile) | `services/render.py` + `services/intro.py` | ✅ |
| Upload artifact + persist URL | `workers/tasks.render_snippet` | ✅ |
| Batch render-all | `POST /sessions/{id}/snippets/render-all` | ✅ |
| Retry session | `POST /sessions/{id}/retry` | ✅ |
| Task status polling | `GET /snippets/tasks/{task_id}` | ✅ |
