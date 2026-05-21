from functools import lru_cache

from supabase import Client, create_client

from app.core.config import get_settings


@lru_cache
def get_supabase_admin() -> Client:
    """Secret-key client. Bypasses RLS — keep server-side only."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_secret_key)


def get_supabase_user(access_token: str) -> Client:
    """Per-request client that runs under the caller's RLS context."""
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_publishable_key)
    client.postgrest.auth(access_token)
    return client
