from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse

from backend.dependencies.auth import get_current_auth_user
from backend.dependencies.database_session import AsyncDatabaseSession
from backend.schemas.plant_readiness import PlantReadiness
from backend.services import plant_readiness as plant_readiness_service
from backend.settings import get_settings

router = APIRouter(
	prefix="/plant-readiness",
	tags=["plant-readiness"],
	dependencies=[Depends(get_current_auth_user)],
)


@router.get(
	"",
	description="""
		Crowding recommendations from the computer vision results: per camera, the latest frame at or before
		`asOf` (default: the newest) with the plants to expand, to check spacing, and closed canopy areas.
	""",
)
async def read_plant_readiness(
	session: AsyncDatabaseSession,
	level: Annotated[int, Query(ge=1, le=2)] = 1,
	as_of: Annotated[
		datetime | None, Query(alias="asOf", description="Farm local time; a timezone is ignored.")
	] = None,
) -> PlantReadiness:
	return await plant_readiness_service.get_plant_readiness(session, level, as_of)


@router.get("/overlays/{image_id}", description="The CV overlay picture (plant outlines, contact lines) of a frame.")
async def read_overlay(session: AsyncDatabaseSession, image_id: str) -> FileResponse:
	path = await plant_readiness_service.overlay_path(session, Path(get_settings().CV_RUNS_DIR), image_id)
	if path is None:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No overlay for this frame")
	return FileResponse(path, media_type="image/jpeg")
