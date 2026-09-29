from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

AlertSeverity = Literal["info", "warning", "critical"]
AlertStatus = Literal["active", "resolved"]
AlertStatusFilter = Literal["active", "resolved", "all"]
AlertResolver = Literal["agent", "user"]


class AlertRead(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)

	alert_id: UUID
	alert_key: str
	severity: AlertSeverity
	title: str
	message: str
	status: AlertStatus
	occurrences: int
	schedule_id: UUID | None = None
	created_at: AwareDatetime
	updated_at: AwareDatetime
	resolved_at: AwareDatetime | None = None
	resolved_by: AlertResolver | None = None
	dismissed_at: AwareDatetime | None = None
