from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class AuthenticatedUser(BaseModel):
	id: UUID


class LoginRequest(BaseModel):
	model_config = ConfigDict(extra="forbid")
	email: str
	password: str


class UpdateUserProfile(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")
	first_name: str | None = Field(default=None, max_length=100)
	last_name: str | None = Field(default=None, max_length=100)

	@field_validator("first_name", "last_name", mode="before")
	@classmethod
	def normalize_name(cls, value: object) -> object:
		return (value.strip() or None) if isinstance(value, str) else value


class UpdateUserPassword(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")
	new_password: str = Field(min_length=8, max_length=200)


class CurrentUserResponse(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	id: UUID
	email: str
	first_name: str | None = None
	last_name: str | None = None
	created_at: datetime
	updated_at: datetime | None = None
	last_login_at: datetime | None = None
