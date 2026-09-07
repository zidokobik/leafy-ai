from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from postgrest.exceptions import APIError

from backend.dependencies.auth import get_current_auth_user
from backend.schemas.monitoring import MonitoringHistoryResponse, MonitorRange
from backend.services.monitoring import get_history
from backend.services.supabase import get_supabase_admin_client, get_supabase_configuration
from backend.settings import Settings, get_settings

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])


@router.get("/history", response_model=MonitoringHistoryResponse)
def monitoring_history(
	_: Annotated[object, Depends(get_current_auth_user)],
	settings: Annotated[Settings, Depends(get_settings)],
	monitor_range: Annotated[MonitorRange, Query(alias="range")] = "24H",
) -> MonitoringHistoryResponse:
	configuration = get_supabase_configuration(settings)
	client = get_supabase_admin_client(configuration.url, configuration.secret_key)
	try:
		points = get_history(client, monitor_range)
	except (APIError, KeyError, TypeError, ValueError) as error:
		raise HTTPException(
			status_code=status.HTTP_502_BAD_GATEWAY,
			detail="Unable to read sensor history",
		) from error
	return MonitoringHistoryResponse(range=monitor_range, points=points)
