"""Load the CV's observations.csv files (one row per frame x planting hole or canopy zone) into plant_observations."""

import csv
from datetime import datetime
from itertools import batched
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db_models.plant_observations import PlantObservation
from backend.schemas.plant_readiness import ObservationKind, PlantStatus

INSERT_BATCH_SIZE = 1000
_BOOLEANS = {"True": True, "False": False}


def _optional_float(value: str) -> float | None:
	"""Blank means "not measurable", never 0."""
	return float(value) if value else None


def _optional_int(value: str) -> int | None:
	return int(value) if value else None


def _boolean(value: str) -> bool:
	if value not in _BOOLEANS:
		raise ValueError(f"Expected True or False, got {value!r}.")
	return _BOOLEANS[value]


def parse_observation(row: dict[str, str]) -> PlantObservation:
	"""Return the typed observation for one observations.csv row (the only place CSV text is converted)."""
	return PlantObservation(
		image_id=row["image_id"],
		model_version=row["model_version"],
		camera_id=row["camera_id"],
		captured_at=datetime.fromisoformat(row["captured_at"]),
		level=int(row["level"]),
		period=row["period"],
		hole_id=row["hole_id"],
		kind=ObservationKind(row["kind"]),
		row=_optional_int(row["row"]),
		col=_optional_int(row["col"]),
		in_frame=_optional_float(row["in_frame"]),
		occupied=_boolean(row["occupied"]),
		coverage=float(row["coverage"]),
		boundary_contact=_optional_float(row["boundary_contact"]),
		contact_along=_optional_float(row["contact_along"]),
		contact_across=_optional_float(row["contact_across"]),
		plant_area_px=_optional_int(row["plant_area_px"]),
		status=PlantStatus(row["status"]),
		confirmed_frames=int(row["confirmed_frames"]),
		flags=[flag for flag in row["flags"].split(";") if flag],
	)


def read_observation_files(runs_dir: Path) -> list[PlantObservation]:
	"""Return every observation in `runs_dir/*/observations.csv`, files in name order."""
	observations: list[PlantObservation] = []
	for path in sorted(runs_dir.glob("*/observations.csv")):
		with path.open(newline="", encoding="utf-8") as file:
			observations.extend(parse_observation(row) for row in csv.DictReader(file))
	return observations


async def insert_observations(session: AsyncSession, observations: list[PlantObservation]) -> int:
	"""Insert the observations, skipping rows already stored; return how many rows were new."""
	inserted = 0
	for batch in batched(observations, INSERT_BATCH_SIZE):
		statement = (
			insert(PlantObservation)
			.values([observation.model_dump(exclude={"id"}) for observation in batch])
			.on_conflict_do_nothing(constraint="plant_observations_unique")
			.returning(PlantObservation.id)
		)
		inserted += len((await session.execute(statement)).all())
	await session.commit()
	return inserted
