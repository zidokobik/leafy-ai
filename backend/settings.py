from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	ENVIRONMENT: Literal["development", "production"] = "development"
	AI_GATEWAY_API_KEY: SecretStr
	AI_MODEL: str
	PUBLIC_SUPABASE_URL: str | None = None
	PUBLIC_SUPABASE_PUBLISHABLE_KEY: str | None = None
	SUPABASE_SECRET_KEY: SecretStr | None = None

	model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
	return Settings()
