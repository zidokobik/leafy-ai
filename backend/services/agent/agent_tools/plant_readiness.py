from datetime import datetime

import ai
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database_session import get_engine
from backend.services import plant_readiness as plant_readiness_service


@ai.tool
async def get_plant_readiness(level: int = 1, as_of: datetime | None = None) -> dict[str, object]:
	"""Which plants need the grower's attention, from the camera-based crowding estimate.

	Returns, per camera, the latest frame at or before the ISO 8601 `as_of` in farm local time (default: the newest),
	the plants to expand first, then the plants touching the next channel, then closed canopy areas,
	plus counts and limitations. Recommendations only: the grower decides and moves plants by hand.
	"""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		readiness = await plant_readiness_service.get_plant_readiness(session, level, as_of)
	return readiness.model_dump(mode="json")
