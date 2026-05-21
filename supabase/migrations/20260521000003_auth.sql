-- Supabase Auth wiring — profiles only.
-- The owner/membership story lives in 04_projects.sql.
-- Idempotent: safe to re-run.

-- ---------------------------------------------------------------------------
-- profiles: app-specific user fields keyed to auth.users.id
-- ---------------------------------------------------------------------------
create table if not exists public.profiles (
    id           uuid primary key references auth.users(id) on delete cascade,
    email        text,
    full_name    text,
    avatar_url   text,
    created_at   timestamptz not null default now(),
    updated_at   timestamptz not null default now()
);

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
    before update on public.profiles
    for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Auto-create a profile row whenever a new auth user signs up.
-- ---------------------------------------------------------------------------
create or replace function public.handle_new_user()
returns trigger
security definer
set search_path = public
language plpgsql as $$
begin
    insert into public.profiles (id, email, full_name, avatar_url)
    values (
        new.id,
        new.email,
        coalesce(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name'),
        new.raw_user_meta_data->>'avatar_url'
    )
    on conflict (id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
    after insert on auth.users
    for each row execute function public.handle_new_user();

-- ---------------------------------------------------------------------------
-- RLS: a user can read and update their own profile row.
-- ---------------------------------------------------------------------------
alter table public.profiles enable row level security;

drop policy if exists "profiles select own"  on public.profiles;
drop policy if exists "profiles update own"  on public.profiles;

create policy "profiles select own"
    on public.profiles for select
    using (auth.uid() = id);

create policy "profiles update own"
    on public.profiles for update
    using (auth.uid() = id)
    with check (auth.uid() = id);
