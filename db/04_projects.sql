-- Projects + per-project membership with roles.
-- Sessions (and their snippets) belong to a project. Access is governed by
-- membership in that project, not by individual user ownership.
-- Idempotent: safe to re-run.

-- ---------------------------------------------------------------------------
-- Role enum: manager > editor > viewer.
--   manager : full control — manage members, edit any session, delete the project
--   editor  : create sessions and edit/delete their own; read all project content
--   viewer  : read-only access to the project
-- ---------------------------------------------------------------------------
do $$
begin
    if not exists (select 1 from pg_type where typname = 'project_role') then
        create type public.project_role as enum ('manager', 'editor', 'viewer');
    end if;
end$$;

-- ---------------------------------------------------------------------------
-- projects
-- ---------------------------------------------------------------------------
create table if not exists public.projects (
    id          bigserial primary key,
    name        text        not null,
    description text,
    created_by  uuid        references auth.users(id) on delete set null,
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

drop trigger if exists projects_set_updated_at on public.projects;
create trigger projects_set_updated_at
    before update on public.projects
    for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- project_members: many-to-many, role per (project, user)
-- ---------------------------------------------------------------------------
create table if not exists public.project_members (
    project_id bigint               not null references public.projects(id) on delete cascade,
    user_id    uuid                 not null references auth.users(id)      on delete cascade,
    role       public.project_role  not null default 'editor',
    joined_at  timestamptz          not null default now(),
    primary key (project_id, user_id)
);

create index if not exists project_members_user_id_idx
    on public.project_members(user_id);

-- ---------------------------------------------------------------------------
-- Auto-add the creator as a manager.
-- ---------------------------------------------------------------------------
create or replace function public.add_project_manager()
returns trigger
security definer
set search_path = public
language plpgsql as $$
begin
    if new.created_by is not null then
        insert into public.project_members (project_id, user_id, role)
        values (new.id, new.created_by, 'manager')
        on conflict (project_id, user_id) do nothing;
    end if;
    return new;
end;
$$;

drop trigger if exists projects_add_manager on public.projects;
create trigger projects_add_manager
    after insert on public.projects
    for each row execute function public.add_project_manager();

-- ---------------------------------------------------------------------------
-- Auto-create a default project on signup.
-- Fires on auth.users insert, creates one project, and the
-- projects_add_manager trigger above then promotes the new user to manager.
-- ---------------------------------------------------------------------------
create or replace function public.create_default_project_for_user()
returns trigger
security definer
set search_path = public
language plpgsql as $$
declare
    display_name text;
    project_name text;
begin
    display_name := coalesce(
        nullif(new.raw_user_meta_data->>'full_name', ''),
        nullif(new.raw_user_meta_data->>'name', '')
    );
    project_name := case
        when display_name is not null then display_name || '''s Project'
        else 'My Project'
    end;

    insert into public.projects (name, created_by)
    values (project_name, new.id);

    return new;
end;
$$;

drop trigger if exists on_auth_user_create_default_project on auth.users;
create trigger on_auth_user_create_default_project
    after insert on auth.users
    for each row execute function public.create_default_project_for_user();

-- ---------------------------------------------------------------------------
-- session: every session belongs to (a) a project and (b) a creator.
-- Access is governed by project membership; user_id is the audit field for
-- "who made this row" and powers the "can edit your own" check below.
-- Columns are NOT NULL on the assumption the table is empty when this runs
-- (fresh setup). If you already have rows, drop the NOT NULL clauses, fill
-- the columns, then re-add NOT NULL.
-- ---------------------------------------------------------------------------
alter table public.session
    add column if not exists user_id    uuid   not null references auth.users(id) on delete cascade,
    add column if not exists project_id bigint not null references public.projects(id) on delete cascade;

create index if not exists session_user_id_idx    on public.session(user_id);
create index if not exists session_project_id_idx on public.session(project_id);

-- ---------------------------------------------------------------------------
-- Membership helpers (SECURITY DEFINER to keep RLS subqueries fast and
-- avoid recursive policy evaluation on project_members itself).
-- ---------------------------------------------------------------------------
create or replace function public.is_project_member(_project_id bigint)
returns boolean
language sql
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.project_members
        where project_id = _project_id and user_id = auth.uid()
    );
$$;

create or replace function public.is_project_manager(_project_id bigint)
returns boolean
language sql
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.project_members
        where project_id = _project_id
          and user_id    = auth.uid()
          and role       = 'manager'
    );
$$;

-- Manager or editor — anyone who can write content.
create or replace function public.is_project_writer(_project_id bigint)
returns boolean
language sql
security definer
set search_path = public
as $$
    select exists (
        select 1 from public.project_members
        where project_id = _project_id
          and user_id    = auth.uid()
          and role in ('manager', 'editor')
    );
$$;

-- ---------------------------------------------------------------------------
-- RLS: projects
-- ---------------------------------------------------------------------------
alter table public.projects enable row level security;

drop policy if exists "projects select if member"    on public.projects;
drop policy if exists "projects insert authed"       on public.projects;
drop policy if exists "projects update if manager"   on public.projects;
drop policy if exists "projects delete if manager"   on public.projects;

create policy "projects select if member"
    on public.projects for select
    using (public.is_project_member(id));

create policy "projects insert authed"
    on public.projects for insert
    with check (auth.uid() is not null and created_by = auth.uid());

create policy "projects update if manager"
    on public.projects for update
    using (public.is_project_manager(id))
    with check (public.is_project_manager(id));

create policy "projects delete if manager"
    on public.projects for delete
    using (public.is_project_manager(id));

-- ---------------------------------------------------------------------------
-- RLS: project_members
-- ---------------------------------------------------------------------------
alter table public.project_members enable row level security;

drop policy if exists "members select if member"    on public.project_members;
drop policy if exists "members insert if manager"   on public.project_members;
drop policy if exists "members update if manager"   on public.project_members;
drop policy if exists "members delete if manager"   on public.project_members;

create policy "members select if member"
    on public.project_members for select
    using (public.is_project_member(project_id));

create policy "members insert if manager"
    on public.project_members for insert
    with check (public.is_project_manager(project_id));

create policy "members update if manager"
    on public.project_members for update
    using (public.is_project_manager(project_id))
    with check (public.is_project_manager(project_id));

create policy "members delete if manager"
    on public.project_members for delete
    using (public.is_project_manager(project_id));

-- ---------------------------------------------------------------------------
-- RLS: session — replace the per-user policies from 03_auth.sql with
-- project-based policies. Members read all project sessions; only the
-- creator or a project admin can mutate.
-- ---------------------------------------------------------------------------
drop policy if exists "session select via project"   on public.session;
drop policy if exists "session insert via project"   on public.session;
drop policy if exists "session update via project"   on public.session;
drop policy if exists "session delete via project"   on public.session;

create policy "session select via project"
    on public.session for select
    using (public.is_project_member(project_id));

create policy "session insert via project"
    on public.session for insert
    with check (
        public.is_project_writer(project_id)
        and user_id = auth.uid()
    );

create policy "session update via project"
    on public.session for update
    using (
        public.is_project_manager(project_id)
        or (public.is_project_writer(project_id) and user_id = auth.uid())
    )
    with check (
        public.is_project_manager(project_id)
        or (public.is_project_writer(project_id) and user_id = auth.uid())
    );

create policy "session delete via project"
    on public.session for delete
    using (
        public.is_project_manager(project_id)
        or (public.is_project_writer(project_id) and user_id = auth.uid())
    );

-- ---------------------------------------------------------------------------
-- RLS: snippet — ownership inherited from session.project_id.
-- ---------------------------------------------------------------------------
drop policy if exists "snippet select via session"   on public.snippet;
drop policy if exists "snippet insert via session"   on public.snippet;
drop policy if exists "snippet update via session"   on public.snippet;
drop policy if exists "snippet delete via session"   on public.snippet;

create policy "snippet select via session"
    on public.snippet for select
    using (
        exists (
            select 1 from public.session s
            where s.id = snippet.session_id
              and public.is_project_member(s.project_id)
        )
    );

create policy "snippet insert via session"
    on public.snippet for insert
    with check (
        exists (
            select 1 from public.session s
            where s.id = snippet.session_id
              and (
                public.is_project_manager(s.project_id)
                or (public.is_project_writer(s.project_id) and s.user_id = auth.uid())
              )
        )
    );

create policy "snippet update via session"
    on public.snippet for update
    using (
        exists (
            select 1 from public.session s
            where s.id = snippet.session_id
              and (
                public.is_project_manager(s.project_id)
                or (public.is_project_writer(s.project_id) and s.user_id = auth.uid())
              )
        )
    );

create policy "snippet delete via session"
    on public.snippet for delete
    using (
        exists (
            select 1 from public.session s
            where s.id = snippet.session_id
              and (
                public.is_project_manager(s.project_id)
                or (public.is_project_writer(s.project_id) and s.user_id = auth.uid())
              )
        )
    );
