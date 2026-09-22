import uuid
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel


class AgentScheduledJobWrite(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

	title: str
	instruction: str
	cron_expression: str

	@field_validator("title", "instruction", "cron_expression")
	@classmethod
	def strip_required_text(cls, value: str) -> str:
		value = value.strip()
		if not value:
			raise ValueError("must not be blank")
		return value

	@field_validator("cron_expression")
	@classmethod
	def validate_cron_expression(cls, value: str) -> str:
		CronTrigger.from_crontab(value)
		return value


class AgentScheduledJobRead(AgentScheduledJobWrite):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

	id: uuid.UUID
	created_at: datetime
