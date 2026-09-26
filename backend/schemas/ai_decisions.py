from typing import Annotated
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel

NonBlankText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class AIDecisionCreate(BaseModel):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")
	summary: NonBlankText
	recommendation: NonBlankText
	schedule_id: UUID | None = None


class AIDecisionRead(AIDecisionCreate):
	model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)
	decision_id: UUID
	created_at: AwareDatetime
