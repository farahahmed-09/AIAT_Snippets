# Migrations

Schema lives in this folder, one timestamped file per change. All
migrations are written to be **idempotent** (`create table if not
exists`, `drop policy if exists` before each `create policy`, etc.) so
re-running them against an existing database is safe.

## Files

| File | Purpose |
|------|---------|
| `20260521000001_schema.sql` | `public.session` + `public.snippet`, `set_updated_at` trigger, RLS enabled |
| `20260521000002_storage.sql` | `snippets` storage bucket + public-read policy |
| `20260521000003_auth.sql` | `public.profiles` mirror of `auth.users` + signup trigger |
| `20260521000004_projects.sql` | `public.projects`, `project_members`, role helpers, project-scoped RLS for `session` and `snippet` |

## Applying to a fresh Supabase project

```bash
# 1. Create a new Supabase project at https://supabase.com/dashboard.
# 2. Link this repo to it (one-time, from the repo root):
supabase link --project-ref <project-ref>

# 3. Push every migration in this folder to the remote db:
supabase db push
```

`supabase db push` reads `supabase/migrations/`, compares against the
`supabase_migrations.schema_migrations` tracking table on the remote,
and applies the missing ones in timestamp order.

## Local development

```bash
supabase start          # boots a local Postgres + Studio in Docker
supabase db reset       # re-applies all migrations against the local db
supabase stop           # tear down
```

The local db is reachable at `postgresql://postgres:postgres@localhost:54322/postgres`
and Studio at `http://localhost:54323`.

## Adding a new migration

```bash
supabase migration new <name>          # creates an empty timestamped file
# write your SQL — remember to make it idempotent
supabase db reset                       # validate locally
supabase db push                        # apply to remote when ready
```

## Notes

- The backend currently uses the **service_role** key, which bypasses
  RLS — so the RLS policies in `20260521000004_projects.sql` only kick
  in once endpoints switch to the per-user client
  (`get_supabase_user(token)` in `backend/app/db/supabase.py`).
- `public.snippet.session_id` cascades on delete, so removing a session
  removes its snippets.
- `session.updated_at` is bumped by a trigger because SQLAlchemy's
  `onupdate` does not fire for writes that go through PostgREST.
- `intro_metadata` is stored as `text` (the legacy app serialised JSON
  to a string). Convert to `jsonb` in a future migration if you want
  native querying.
