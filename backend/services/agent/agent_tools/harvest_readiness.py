from datetime import datetime

import ai
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database_session import get_engine
from backend.services import harvest_readiness as harvest_readiness_service


@ai.tool
async def get_harvest_readiness(as_of: datetime | None = None) -> dict[str, object]:
	"""Which Level 2 batches are due for harvest: due 7 days after the plants moved up from Level 1.

	Returns every batch moved at or before the ISO 8601 `as_of` in farm local time (default: now), with days on
	Level 2, due time and status (growing, harvest_tomorrow, harvest_due, harvested), plus limitations.
	A date rule, not a camera measurement: the grower checks the plants before harvesting.
	"""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		readiness = await harvest_readiness_service.get_harvest_readiness(session, as_of)
	return readiness.model_dump(mode="json")
