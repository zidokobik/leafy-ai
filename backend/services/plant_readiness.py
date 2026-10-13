"""Grower recommendations from the CV's plant observations: per camera, the latest frame at or before a time."""

import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from backend.db_models.plant_observations import PlantObservation
from backend.schemas.plant_readiness import (
	CameraReadiness,
	GrowerAction,
	ObservationKind,
	PlantReadiness,
	PlantStatus,
	Recommendation,
)

# The CV's CONTACT_CROWDED: leaves count as touching from half of the gap lines closed.
CONTACT_TOUCHING = 0.5
CONTACT_DECIMALS = 4

MESSAGES: dict[GrowerAction, str] = {
	GrowerAction.EXPAND_CHANNEL: "Ready: expand this channel today",
	GrowerAction.CHECK_SPACING: "Plants touching the next channel: check spacing",
	GrowerAction.CHECK_CANOPY: "Ready: check today (closed canopy area)",
}
# Same-channel crowding first: channel expansion is what fixes it (agreed with Pearl, 12 Oct).
ACTION_ORDER: dict[GrowerAction, int] = {
	GrowerAction.EXPAND_CHANNEL: 1,
	GrowerAction.CHECK_SPACING: 2,
	GrowerAction.CHECK_CANOPY: 3,
}
SUMMARY_LABELS: dict[GrowerAction, tuple[str, str]] = {
	GrowerAction.EXPAND_CHANNEL: ("plant to expand", "plants to expand"),
	GrowerAction.CHECK_SPACING: ("plant to check spacing", "plants to check spacing"),
	GrowerAction.CHECK_CANOPY: ("canopy area", "canopy areas"),
}
NOTHING_TO_DO = "Nothing to do"
# Frame file names as the CV writes them, e.g. level1_camera2_20261002_180016.jpg.
IMAGE_ID_PATTERN = re.compile(r"level\d+_camera\d+_\d{8}_\d{6}\.jpg")

LIMITATIONS = (
	"Readiness comes from a camera-based estimate and the grower should confirm on site. Alerts can come about a day "
	"late, and about 2 days late on camera 1's far canopy zone. Camera 3 grows a different leafy crop, measured with a "
	"basil-trained filter. Cameras 1 and 2 see some of the same plants and report separately. After the trays are "
	"rearranged, new hole maps are needed before alerts resume. The archived data ends on 8 Oct 2026."
)


def grower_action(observation: PlantObservation) -> GrowerAction:
	"""Return what to ask the grower for a `ready` row: zones -> canopy, holes -> the direction that touches most."""
	if observation.kind == ObservationKind.ZONE:
		return GrowerAction.CHECK_CANOPY
	along = observation.contact_along or 0.0
	across = observation.contact_across or 0.0
	# Along >= 0.5 wins; below 0.5 on both sides (crowded through smoothing) the larger direction decides.
	if along >= CONTACT_TOUCHING or (across < CONTACT_TOUCHING and along >= across):
		return GrowerAction.EXPAND_CHANNEL
	return GrowerAction.CHECK_SPACING


def _rounded(value: float | None) -> float | None:
	"""Return a contact back at the CSV's 4 decimals (the table stores single-precision `real`)."""
	return None if value is None else round(value, CONTACT_DECIMALS)


def to_recommendation(observation: PlantObservation) -> Recommendation:
	"""Return the grower recommendation for one `ready` row."""
	action = grower_action(observation)
	return Recommendation(
		hole_id=observation.hole_id,
		action=action,
		message=MESSAGES[action],
		row=observation.row,
		col=observation.col,
		contact_along=_rounded(observation.contact_along),
		contact_across=_rounded(observation.contact_across),
		confirmed_frames=observation.confirmed_frames,
	)


def camera_readiness(frame: list[PlantObservation]) -> CameraReadiness:
	"""Return status counts and sorted recommendations for the rows of one camera frame."""
	recommendations = [to_recommendation(row) for row in frame if row.status == PlantStatus.READY]
	recommendations.sort(key=lambda item: (ACTION_ORDER[item.action], item.hole_id))
	return CameraReadiness(
		camera_id=frame[0].camera_id,
		period=frame[0].period,
		captured_at=frame[0].captured_at,
		image_id=frame[0].image_id,
		status_counts=dict(Counter(PlantStatus(row.status) for row in frame)),
		recommendations=recommendations,
	)


def summarise(cameras: list[CameraReadiness]) -> str:
	"""Return e.g. "25 plants to expand, 19 plants to check spacing, 1 canopy area", or "Nothing to do"."""
	counts = Counter(item.action for camera in cameras for item in camera.recommendations)
	parts = []
	for action in sorted(counts, key=ACTION_ORDER.__getitem__):
		singular, plural = SUMMARY_LABELS[action]
		parts.append(f"{counts[action]} {singular if counts[action] == 1 else plural}")
	return ", ".join(parts) or NOTHING_TO_DO


async def _current_model_version(session: AsyncSession) -> str | None:
	"""Return the model version loaded last (a CV fix is loaded as a new version), or None if the table is empty."""
	statement = select(PlantObservation.model_version).order_by(PlantObservation.id.desc()).limit(1)
	return (await session.execute(statement)).scalar_one_or_none()


async def _latest_frame_times(
	session: AsyncSession, level: int, model_version: str, as_of: datetime | None
) -> dict[str, datetime]:
	"""Return each camera's newest frame time at or before `as_of`; cameras without a frame are left out."""
	statement = (
		select(PlantObservation.camera_id, sa.func.max(PlantObservation.captured_at))
		.where(PlantObservation.level == level, PlantObservation.model_version == model_version)
		.group_by(PlantObservation.camera_id)
	)
	if as_of is not None:
		statement = statement.where(PlantObservation.captured_at <= as_of)
	return dict((await session.execute(statement)).tuples().all())


async def _frame_observations(
	session: AsyncSession, model_version: str, frame_times: dict[str, datetime]
) -> dict[str, list[PlantObservation]]:
	"""Return the rows of each camera's selected frame, keyed by camera id."""
	statement = select(PlantObservation).where(
		PlantObservation.model_version == model_version,
		sa.tuple_(PlantObservation.camera_id, PlantObservation.captured_at).in_(list(frame_times.items())),
	)
	frames: dict[str, list[PlantObservation]] = {}
	for observation in (await session.execute(statement)).scalars():
		frames.setdefault(observation.camera_id, []).append(observation)
	return frames


async def overlay_path(session: AsyncSession, runs_dir: Path, image_id: str) -> Path | None:
	"""Return the CV overlay picture of a stored frame, or None if the frame or its file is unknown.

	The path is built only from values stored in the table, never from the request alone.
	"""
	if not IMAGE_ID_PATTERN.fullmatch(image_id):
		return None
	statement = (
		select(PlantObservation.camera_id, PlantObservation.period, PlantObservation.image_id)
		.where(PlantObservation.image_id == image_id)
		.limit(1)
	)
	frame = (await session.execute(statement)).first()
	if frame is None:
		return None
	camera_id, period, stored_image_id = frame
	path = runs_dir / f"{camera_id}_{period}" / "overlays" / stored_image_id
	return path if path.is_file() else None


async def get_plant_readiness(session: AsyncSession, level: int = 1, as_of: datetime | None = None) -> PlantReadiness:
	"""Return, per camera, the latest frame at or before `as_of` (None = newest) with its grower recommendations.

	Frame times are farm local time without a timezone, so a timezone on `as_of` is dropped, not converted.
	"""
	if as_of is not None:
		as_of = as_of.replace(tzinfo=None)
	model_version = await _current_model_version(session)
	cameras: list[CameraReadiness] = []
	if model_version is not None:
		frame_times = await _latest_frame_times(session, level, model_version, as_of)
		if frame_times:
			frames = await _frame_observations(session, model_version, frame_times)
			cameras = [camera_readiness(frames[camera_id]) for camera_id in sorted(frames)]
	return PlantReadiness(
		level=level,
		as_of=as_of,
		model_version=model_version if cameras else None,
		cameras=cameras,
		summary=summarise(cameras),
		limitations=LIMITATIONS,
	)
