from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

ProposalStatus = Literal["pending", "running", "completed", "stopped", "rejected", "expired", "failed"]


class ProposalRead(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

	id: UUID
	device_id: UUID | None = None
	device_name: str
	duration_seconds: int
	reason: str
	status: ProposalStatus
	schedule_id: UUID | None = None
	created_at: AwareDatetime
	expires_at: AwareDatetime
	reviewed_by: UUID | None = None
	reviewer_email: str | None = None
	reviewed_at: AwareDatetime | None = None
	started_at: AwareDatetime | None = None
	ends_at: AwareDatetime | None = None
	finished_at: AwareDatetime | None = None
	result_message: str | None = None
