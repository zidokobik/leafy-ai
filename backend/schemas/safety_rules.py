from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

ActionType = Literal["run_for_duration"]
PositiveSeconds = Annotated[int, Field(strict=True, gt=0, le=2147483647)]
CooldownSeconds = Annotated[int, Field(strict=True, ge=0, le=2147483647)]


class SafetyRuleWrite(BaseModel):
	"""Full rule payload; device/action uniqueness is enforced by the database."""

	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")
	device_id: UUID
	action_type: ActionType = "run_for_duration"
	max_duration_seconds: PositiveSeconds
	cooldown_seconds: CooldownSeconds = 0
	enabled: bool = Field(default=True, strict=True)


class SafetyRuleRead(SafetyRuleWrite):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
	rule_id: UUID
