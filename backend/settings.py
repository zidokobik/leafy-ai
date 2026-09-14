from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	ENVIRONMENT: Literal["development", "production"] = "development"
	AI_GATEWAY_API_KEY: SecretStr
	AI_MODEL: str

	DATABASE_URI: SecretStr

	JWT_SECRET_KEY: SecretStr
	SESSION_COOKIE_NAME: str = "leafy_session"
	SESSION_TTL_SECONDS: int = 60 * 60 * 24 * 7

	model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
	return Settings()
