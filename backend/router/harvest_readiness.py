from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.harvest_readiness import HarvestReadiness
from backend.services import harvest_readiness as harvest_readiness_service

router = APIRouter(
	prefix="/harvest-readiness",
	tags=["harvest-readiness"],
	dependencies=[Depends(get_current_auth_user)],
)


@router.get(
	"",
	description="""
		Level 2 batches moved at or before `asOf` (default: now, farm time) with their harvest status: due 7 days
		after the plants moved up from Level 1.
	""",
)
async def read_harvest_readiness(
	session: AsyncDatabaseSession,
	as_of: Annotated[
		datetime | None, Query(alias="asOf", description="Farm local time; a timezone is ignored.")
	] = None,
) -> HarvestReadiness:
	return await harvest_readiness_service.get_harvest_readiness(session, as_of)
