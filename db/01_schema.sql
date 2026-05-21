-- SmartCut AI / Snippets — fresh-Supabase schema.
-- Run this in the SQL editor of a brand-new Supabase project.
-- Idempotent: safe to re-run.

-- ---------------------------------------------------------------------------
-- session
-- ---------------------------------------------------------------------------
create table if not exists public.session (
    id                     bigserial primary key,
    name                   text        not null,
    module                 text,
    drive_link             text,

    speaker_name           text,
    speaker_title          text,
    speaker_image_url      text,
    intro_video_url        text,
    background_image_url   text,

    job_status             text        not null default 'Pending',

    source_video_stored    boolean              default false,
    last_accessed_at       timestamptz,

    created_at             timestamptz not null default now(),
    started_at             timestamptz,
    updated_at             timestamptz not null default now(),
    completed_at           timestamptz
);

-- ---------------------------------------------------------------------------
-- snippet
-- ---------------------------------------------------------------------------
create table if not exists public.snippet (
    id              bigserial primary key,
    session_id      bigint      not null
                    references public.session(id) on delete cascade,
    name            text        not null,
    summary         text,
    start_second    integer     not null,
    end_second      integer     not null,
    intro_id        integer,
    style_name      text,
    intro_metadata  text,                       -- JSON serialized as text
    storage_link    text,
    is_persisted    boolean              default false,
    created_at      timestamptz not null default now()
);

create index if not exists snippet_session_id_idx
    on public.snippet(session_id);

-- ---------------------------------------------------------------------------
-- updated_at trigger for session (SQLAlchemy onupdate doesn't fire over PostgREST)
-- ---------------------------------------------------------------------------
create or replace function public.set_updated_at()
returns trigger as $$
begin
    new.updated_at := now();
    return new;
end;
$$ language plpgsql;

drop trigger if exists session_set_updated_at on public.session;
create trigger session_set_updated_at
    before update on public.session
    for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- RLS: lock tables down. The backend connects with the service_role key,
-- which bypasses RLS, so leaving zero policies blocks anon/auth users
-- while keeping the API working.
-- ---------------------------------------------------------------------------
alter table public.session enable row level security;
alter table public.snippet enable row level security;
