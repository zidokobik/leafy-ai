from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PlantStatus(StrEnum):
	"""Readiness status the CV assigns to a hole or zone in one frame; only `ready` is shown to the grower."""

	EMPTY = "empty"
	GROWING = "growing"
	CANDIDATE = "candidate"
	READY = "ready"
	UNCERTAIN = "uncertain"


class ObservationKind(StrEnum):
	"""A planting hole or a canopy zone (dense area measured as closure, not per plant)."""

	HOLE = "hole"
	ZONE = "zone"


class GrowerAction(StrEnum):
	"""What the grower is asked to check for a `ready` hole or zone."""

	EXPAND_CHANNEL = "expand_channel"
	CHECK_SPACING = "check_spacing"
	CHECK_CANOPY = "check_canopy"


# camelCase in API responses; the agent tool dumps field names (snake_case).
_API_CONFIG = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Recommendation(BaseModel):
	model_config = _API_CONFIG

	hole_id: str  # "L1-C2-R06-H03", or a zone id such as "L1-C1-Z-dense_far"
	action: GrowerAction
	message: str
	row: int | None
	col: int | None
	contact_along: float | None
	contact_across: float | None
	confirmed_frames: int


class CameraReadiness(BaseModel):
	model_config = _API_CONFIG

	camera_id: str
	period: str  # layout the frame belongs to, e.g. "P3"
	captured_at: datetime  # farm local time, no timezone
	image_id: str
	status_counts: dict[PlantStatus, int]
	recommendations: list[Recommendation]  # expand first, then check spacing, then canopy; then by hole_id


class PlantReadiness(BaseModel):
	model_config = _API_CONFIG

	level: int
	as_of: datetime | None
	model_version: str | None  # None when no frame exists at or before as_of
	cameras: list[CameraReadiness]
	summary: str
	limitations: str
