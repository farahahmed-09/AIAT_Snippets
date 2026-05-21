-- Intro asset library: per-project reusable intro videos + thumbnails.
-- Files live in the existing `snippets` storage bucket under the prefix
-- intros/<project_id>/<uuid>.<ext>. The bucket is public-read, so the
-- public URL serves the asset without a signed URL.
-- Idempotent: safe to re-run.

create table if not exists public.intro_asset (
    id              bigserial primary key,
    project_id      bigint      not null references public.projects(id) on delete cascade,
    name            text        not null,
    video_path      text        not null,  -- key inside the `snippets` bucket
    thumbnail_path  text,
    created_by      uuid        references auth.users(id) on delete set null,
    created_at      timestamptz not null default now()
);

create index if not exists intro_asset_project_id_idx
    on public.intro_asset(project_id);

alter table public.intro_asset enable row level security;

drop policy if exists "intro_asset select via project" on public.intro_asset;
drop policy if exists "intro_asset insert via project" on public.intro_asset;
drop policy if exists "intro_asset delete via project" on public.intro_asset;

create policy "intro_asset select via project"
    on public.intro_asset for select
    using (public.is_project_member(project_id));

create policy "intro_asset insert via project"
    on public.intro_asset for insert
    with check (
        public.is_project_writer(project_id)
        and (created_by is null or created_by = auth.uid())
    );

create policy "intro_asset delete via project"
    on public.intro_asset for delete
    using (
        public.is_project_manager(project_id)
        or (public.is_project_writer(project_id) and created_by = auth.uid())
    );
