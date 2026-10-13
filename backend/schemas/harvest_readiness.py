from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# camelCase in API responses; the agent tool dumps field names (snake_case).
_API_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class HarvestStatus(StrEnum):
	"""Where a Level 2 batch is in its 7-day harvest window."""

	GROWING = "growing"
	HARVEST_TOMORROW = "harvest_tomorrow"
	HARVEST_DUE = "harvest_due"
	HARVESTED = "harvested"


class BatchHarvest(BaseModel):
	model_config = _API_CONFIG

	batch_id: int
	moved_at: datetime  # farm local time, no timezone
	due_at: datetime
	harvested_at: datetime | None
	days_on_level2: float
	status: HarvestStatus
	message: str
	note: str


class HarvestReadiness(BaseModel):
	model_config = _API_CONFIG

	as_of: datetime  # farm local time the statuses are computed for
	batches: list[BatchHarvest]  # newest move first
	summary: str
	limitations: str
