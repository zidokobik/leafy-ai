from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.sensors import SensorHistory, SensorReading
from backend.services import sensors as sensor_service

router = APIRouter(
	prefix="/sensors",
	tags=["sensors"],
	dependencies=[Depends(get_current_auth_user)],
)


@router.get(
	"/history",
	description="""
		Sensor readings for the inclusive `before` to `end` interval, averaged into adaptive buckets and
		ordered oldest first.
	""",
)
async def read_sensor_history(
	session: AsyncDatabaseSession,
	before: Annotated[datetime, Query(description="Inclusive UTC interval start.")],
	end: Annotated[datetime, Query(description="Inclusive UTC interval end.")],
) -> SensorHistory:
	try:
		return await sensor_service.get_history(session, before, end)
	except ValueError as error:
		raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.get("/latest", description="The most recent raw sensor reading.")
async def read_latest_sensor_reading(session: AsyncDatabaseSession) -> SensorReading:
	reading = await sensor_service.get_latest_reading(session)
	if reading is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sensor readings are available")
	return reading
