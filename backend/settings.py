from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
	ENVIRONMENT: Literal["development", "production"] = "development"
	AI_GATEWAY_API_KEY: str
	AI_MODEL: str

	model_config = SettingsConfigDict(env_file=".env")
