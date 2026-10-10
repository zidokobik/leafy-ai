from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

EmailStatus = Literal["sent", "failed"]
EmailTrigger = Literal["agent", "user"]

# Light shape check only; real validation is the SMTP server rejecting the address.
EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class EmailRecipientCreate(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	email: str = Field(pattern=EMAIL_PATTERN, max_length=254)
	label: str | None = Field(default=None, max_length=120)


class EmailRecipientUpdate(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	enabled: bool


class EmailRecipientRead(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

	recipient_id: UUID
	email: str
	label: str | None = None
	enabled: bool
	created_at: AwareDatetime


class EmailLogRead(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

	email_id: UUID
	recipients: list[str]
	subject: str
	status: EmailStatus
	error: str | None = None
	schedule_id: UUID | None = None
	triggered_by: EmailTrigger
	created_at: AwareDatetime
