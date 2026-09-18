from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.monitoring import MonitoringHistoryResponse, MonitoringLatestResponse, MonitorRange
from backend.services.monitoring import get_history, get_latest

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/latest", response_model=MonitoringLatestResponse)
async def read_latest_monitoring(
	_: Annotated[object, Depends(get_current_auth_user)],
	session: AsyncDatabaseSession,
) -> MonitoringLatestResponse:
	latest = await get_latest(session)
	if latest is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No sensor data is available")
	return latest


@router.get("/history", response_model=MonitoringHistoryResponse)
async def read_monitoring_history(
	_: Annotated[object, Depends(get_current_auth_user)],
	session: AsyncDatabaseSession,
	monitor_range: Annotated[MonitorRange, Query(alias="range")] = "24H",
) -> MonitoringHistoryResponse:
	return MonitoringHistoryResponse(range=monitor_range, points=await get_history(session, monitor_range))
