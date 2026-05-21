# Supabase bootstrap

SQL to initialize a fresh Supabase project for the Snippets app.

## Files

| File                | What it does                                                                 |
| ------------------- | ---------------------------------------------------------------------------- |
| `01_schema.sql`     | Creates `public.session` and `public.snippet`, index, `updated_at` trigger, enables RLS. |
| `02_storage.sql`    | Creates the `snippets` storage bucket (public read) and policies.            |
| `03_auth.sql`       | Adds `public.profiles` mirroring `auth.users`, with a trigger that auto-creates a profile row on signup. |
| `04_projects.sql`   | Adds `public.projects` + `public.project_members` (roles: `manager`/`editor`/`viewer`), membership helpers, `session.user_id` + `session.project_id` (both `NOT NULL`), auto-creates a default project on signup, and installs all session/snippet RLS policies. |

Both scripts are idempotent — safe to re-run.

## Run

1. Create a new Supabase project.
2. Open **SQL Editor** in the dashboard.
3. Paste and run `01_schema.sql`.
4. Paste and run `02_storage.sql`.
5. Copy the project URL and the **service_role** key from **Project Settings → API**.
6. Update `.env`:
   ```
   SUPABASE_URL=https://<project-ref>.supabase.co
   SUPABASE_KEY=<service_role_key>
   SUPABASE_BUCKET=snippets
   ```
7. Restart the app: `docker compose restart api worker beat`.

## Notes

- The backend uses the `service_role` key, which bypasses RLS, so no read/write policies are needed on the tables. RLS is enabled to block anon/authenticated direct access.
- `public.snippet.session_id` cascades on delete, so removing a session removes its snippets.
- `session.updated_at` is bumped by a trigger because SQLAlchemy's `onupdate` does not fire for writes that go through PostgREST.
- `intro_metadata` is stored as `text` (the app serializes JSON to a string). Convert to `jsonb` later if you want native querying.
