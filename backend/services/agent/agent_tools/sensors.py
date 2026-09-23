from datetime import datetime

import ai
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database_session import get_engine
from backend.services import sensors as sensor_service


@ai.tool
async def get_sensor_history(before: datetime, end: datetime) -> dict[str, object]:
	"""Get bucketed sensor readings in the inclusive ISO 8601 `before` to `end` interval."""
	async with AsyncSession(get_engine(), expire_on_commit=False) as session:
		history = await sensor_service.get_history(session, before, end)
	return history.model_dump(mode="json")
