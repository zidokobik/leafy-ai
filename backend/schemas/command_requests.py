from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, FutureDatetime
from pydantic.alias_generators import to_camel

from backend.schemas.ai_decisions import NonBlankText
from backend.schemas.safety_rules import ActionType, PositiveSeconds

CommandStatus = Literal[
	"pending_approval",
	"blocked",
	"approved",
	"rejected",
	"expired",
	"executing",
	"succeeded",
	"failed",
	"unknown",
]


class CommandRequestCreate(BaseModel):
	"""Only proposed parameters; status, reviewer and execution fields are server-owned."""

	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")
	decision_id: UUID | None = None
	device_id: UUID
	action_type: ActionType = "run_for_duration"
	duration_seconds: PositiveSeconds
	reason: NonBlankText
	expires_at: Annotated[AwareDatetime, FutureDatetime]


class CommandRequestRead(BaseModel):
	# Separate from Create: stored requests may already be expired.
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
	request_id: UUID
	decision_id: UUID | None = None
	device_id: UUID
	action_type: ActionType
	duration_seconds: int
	reason: str
	status: CommandStatus
	reviewed_by: UUID | None = None
	reviewed_at: AwareDatetime | None = None
	created_at: AwareDatetime
	expires_at: AwareDatetime
	started_at: AwareDatetime | None = None
	finished_at: AwareDatetime | None = None
	result_message: str | None = None


class CommandReviewRequest(BaseModel):
	"""The authenticated reviewer is supplied by the backend, never this payload."""

	model_config = ConfigDict(extra="forbid")
	action: Literal["approve", "reject"]
