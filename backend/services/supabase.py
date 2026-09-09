from functools import lru_cache

from fastapi import HTTPException, status
from supabase import Client, ClientOptions, create_client

from backend.settings import Settings


class SupabaseConfiguration:
	def __init__(self, url: str, publishable_key: str, secret_key: str) -> None:
		self.url = url.rstrip("/")
		self.publishable_key = publishable_key
		self.secret_key = secret_key


def get_supabase_configuration(settings: Settings) -> SupabaseConfiguration:
	if not settings.PUBLIC_SUPABASE_URL or not settings.PUBLIC_SUPABASE_PUBLISHABLE_KEY or not settings.SUPABASE_SECRET_KEY:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail="Supabase is not configured on the API server",
		)

	return SupabaseConfiguration(
		url=settings.PUBLIC_SUPABASE_URL,
		publishable_key=settings.PUBLIC_SUPABASE_PUBLISHABLE_KEY,
		secret_key=settings.SUPABASE_SECRET_KEY.get_secret_value(),
	)


@lru_cache
def get_supabase_auth_client(url: str, publishable_key: str) -> Client:
	return create_client(
		url,
		publishable_key,
		options=ClientOptions(auto_refresh_token=False, persist_session=False),
	)


@lru_cache
def get_supabase_admin_client(url: str, secret_key: str) -> Client:
	return create_client(
		url,
		secret_key,
		options=ClientOptions(auto_refresh_token=False, persist_session=False),
	)
