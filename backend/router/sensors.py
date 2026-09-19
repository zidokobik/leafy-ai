from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.sensors import SensorHistory, SensorRange, SensorReading
from backend.services import sensors as sensor_service

router = APIRouter(
	prefix="/sensors",
	tags=["sensors"],
	dependencies=[Depends(get_current_auth_user)],
)


@router.get(
	"/history",
	description="""
	Sensor readings for the requested range, averaged into fixed buckets and ordered oldest first.
	Buckets are 5 minutes for `24h`, 1 hour for `7d` and 4 hours for `30d`.
	""",
)
async def read_sensor_history(
	session: AsyncDatabaseSession,
	sensor_range: Annotated[SensorRange, Query(alias="range")] = "24h",
) -> SensorHistory:
	return await sensor_service.get_history(session, sensor_range)


@router.get("/latest", description="The most recent raw sensor reading.")
async def read_latest_sensor_reading(session: AsyncDatabaseSession) -> SensorReading:
	reading = await sensor_service.get_latest_reading(session)
	if reading is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sensor readings are available")
	return reading
