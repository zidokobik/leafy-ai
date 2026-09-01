from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class AuthenticatedUser(BaseModel):
	id: UUID
	email: str | None = None


class CurrentUserResponse(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	id: UUID
	email: str
	first_name: str | None = None
	last_name: str | None = None
	roles: list[str] = Field(default_factory=list)
	created_at: datetime
	updated_at: datetime | None = None
	last_login_at: datetime | None = None
