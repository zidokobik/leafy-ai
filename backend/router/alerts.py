from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.alerts import AlertRead, AlertStatusFilter
from backend.services import alerts as alert_service

router = APIRouter(prefix="/alerts", tags=["alerts"], dependencies=[Depends(get_current_auth_user)])


@router.get("", response_model=list[AlertRead], description="Alerts ordered by severity, most recently raised first.")
async def list_alerts(
	session: AsyncDatabaseSession,
	status: AlertStatusFilter = "active",
	limit: Annotated[int, Query(ge=1, le=100)] = 50,
	offset: Annotated[int, Query(ge=0)] = 0,
):
	return await alert_service.list_alerts(session, status, limit, offset)


@router.post(
	"/{alert_id}/dismiss",
	response_model=AlertRead,
	description="Hide an active alert from the dashboard pin without resolving it. Idempotent.",
)
async def dismiss_alert(alert_id: UUID, session: AsyncDatabaseSession):
	try:
		return await alert_service.dismiss_alert(session, alert_id)
	except alert_service.AlertNotFoundError as error:
		raise HTTPException(404, str(error)) from error


@router.post(
	"/{alert_id}/resolve", response_model=AlertRead, description="Explicitly mark an alert resolved. Idempotent."
)
async def resolve_alert(alert_id: UUID, session: AsyncDatabaseSession):
	try:
		return await alert_service.resolve_alert(session, alert_id, resolved_by="user")
	except alert_service.AlertNotFoundError as error:
		raise HTTPException(404, str(error)) from error
