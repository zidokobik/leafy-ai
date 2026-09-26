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
	# Defaults to Secure cookies in production. Set to false only if the app is
	# temporarily served without HTTPS (e.g. testing on a VPS by bare IP);
	# browsers silently refuse to store Secure cookies over plain HTTP.
	SESSION_COOKIE_SECURE: bool | None = None

	# Camera image sync. The images come from the AWS's API as short-lived presigned S3 links, so
	# an hourly job copies them into Supabase Storage. The job is skipped while any value is unset.
	STUDENT_CLIENT_ID: str | None = None
	STUDENT_USERNAME: str | None = None
	STUDENT_PASSWORD: SecretStr | None = None
	SUPABASE_URL: str | None = None
	SUPABASE_SERVICE_KEY: SecretStr | None = None
	CAMERA_BUCKET: str = "images"

	model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
	return Settings()
