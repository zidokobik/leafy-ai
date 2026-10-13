# Frame, move and harvest times are farm local time without a timezone, as stored in the database.
# ruff: noqa: DTZ001
import csv
import io
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.dialects import postgresql

from backend.db_models.plant_observations import PlantObservation
from backend.schemas.plant_readiness import GrowerAction, ObservationKind, PlantStatus
from backend.services.plant_observations import (
	INSERT_BATCH_SIZE,
	insert_observations,
	parse_observation,
	read_observation_files,
)
from backend.services.plant_readiness import (
	MESSAGES,
	NOTHING_TO_DO,
	camera_readiness,
	get_plant_readiness,
	grower_action,
	overlay_path,
	summarise,
)

HEADER = (
	"image_id,model_version,camera_id,captured_at,level,period,hole_id,kind,row,col,in_frame,occupied,coverage,"
	"boundary_contact,contact_along,contact_across,plant_area_px,status,confirmed_frames,flags"
)
VERSION = "mobilesam-vit_t|filter-c338d180|metrics-v3|rule-v5"
# Real rows from cv/data/runs/level1_camera1_P3/observations.csv (and one with two flags).
HOLE_LINE = (
	f"level1_camera1_20260930_110023.jpg,{VERSION},level1_camera1,2026-09-30T11:00:23,1,P3,L1-C1-R01-H02,hole,1,2,"
	"1.00,True,0.7128,0.4444,0.1111,0.4444,12374,growing,0,"
)
ZONE_LINE = (
	f"level1_camera1_20260930_110023.jpg,{VERSION},level1_camera1,2026-09-30T11:00:23,1,P3,L1-C1-Z-dense_far,zone,,,,"
	"True,0.7943,,,,,growing,0,zone"
)
EDGE_LINE = (
	f"level1_camera2_20260930_110024.jpg,{VERSION},level1_camera2,2026-09-30T11:00:24,1,P3,L1-C2-R08-H01,hole,8,1,"
	"0.62,False,0.0213,,,,,uncertain,0,edge_of_frame;estimated_position"
)


def csv_row(line: str) -> dict[str, str]:
	return next(csv.DictReader(io.StringIO(f"{HEADER}\n{line}\n")))


def observation(
	hole_id: str = "L1-C2-R01-H01",
	status: PlantStatus = PlantStatus.READY,
	along: float | None = 0.0,
	across: float | None = 0.0,
	kind: ObservationKind = ObservationKind.HOLE,
	camera_id: str = "level1_camera2",
) -> PlantObservation:
	return PlantObservation(
		image_id=f"{camera_id}_20261002_180016.jpg",
		model_version=VERSION,
		camera_id=camera_id,
		captured_at=datetime(2026, 10, 2, 18, 0, 16),
		level=1,
		period="P3",
		hole_id=hole_id,
		kind=kind,
		row=1,
		col=1,
		occupied=True,
		coverage=0.8,
		contact_along=along,
		contact_across=across,
		status=status,
		confirmed_frames=4,
	)


# --- parse_observation / read_observation_files ---


def test_parse_hole_row_types():
	parsed = parse_observation(csv_row(HOLE_LINE))
	assert parsed.captured_at == datetime(2026, 9, 30, 11, 0, 23)
	assert parsed.kind is ObservationKind.HOLE and parsed.status is PlantStatus.GROWING
	assert (parsed.level, parsed.row, parsed.col, parsed.plant_area_px) == (1, 1, 2, 12374)
	assert parsed.occupied is True
	assert (parsed.contact_along, parsed.contact_across, parsed.boundary_contact) == (0.1111, 0.4444, 0.4444)
	assert parsed.flags == []


def test_parse_blank_numbers_are_none_not_zero():
	parsed = parse_observation(csv_row(ZONE_LINE))
	assert parsed.kind is ObservationKind.ZONE
	assert parsed.row is None and parsed.col is None and parsed.in_frame is None
	assert parsed.contact_along is None and parsed.contact_across is None and parsed.plant_area_px is None
	assert parsed.flags == ["zone"]


def test_parse_flags_and_false():
	parsed = parse_observation(csv_row(EDGE_LINE))
	assert parsed.flags == ["edge_of_frame", "estimated_position"]
	assert parsed.occupied is False
	assert parsed.status is PlantStatus.UNCERTAIN


def test_parse_rejects_unknown_values():
	for column, value in [("occupied", "yes"), ("status", "crowded"), ("kind", "tray")]:
		row = csv_row(HOLE_LINE)
		row[column] = value
		with pytest.raises(ValueError):
			parse_observation(row)


def test_read_observation_files(tmp_path):
	for folder, line in [("level1_camera2_P3", EDGE_LINE), ("level1_camera1_P3", f"{HOLE_LINE}\n{ZONE_LINE}")]:
		(tmp_path / folder).mkdir()
		(tmp_path / folder / "observations.csv").write_text(f"{HEADER}\n{line}\n", encoding="utf-8")
	(tmp_path / "notes.csv").write_text("not an observations file", encoding="utf-8")

	observations = read_observation_files(tmp_path)
	assert [item.hole_id for item in observations] == ["L1-C1-R01-H02", "L1-C1-Z-dense_far", "L1-C2-R08-H01"]


@pytest.mark.asyncio
async def test_insert_observations_batches_and_skips_existing():
	observations = [observation(hole_id=f"L1-C2-R01-H{index:04d}") for index in range(2 * INSERT_BATCH_SIZE + 5)]
	session = MagicMock()
	# 1st batch all new, 2nd batch all already stored, last batch 3 of 5 new.
	results = [MagicMock(), MagicMock(), MagicMock()]
	for result, new in zip(results, [INSERT_BATCH_SIZE, 0, 3], strict=True):
		result.all.return_value = [(index,) for index in range(new)]
	session.execute = AsyncMock(side_effect=results)
	session.commit = AsyncMock()

	assert await insert_observations(session, observations) == INSERT_BATCH_SIZE + 3
	assert session.execute.await_count == 3
	sql = str(session.execute.await_args_list[0].args[0].compile(dialect=postgresql.dialect()))
	assert "ON CONFLICT ON CONSTRAINT plant_observations_unique DO NOTHING" in sql
	assert "(id," not in sql, "the identity column must be left to the database"
	session.commit.assert_awaited_once()


# --- the grower message rule ---


@pytest.mark.parametrize(
	("along", "across", "expected"),
	[
		(0.67, 0.0, GrowerAction.EXPAND_CHANNEL),  # touching along the channel
		(0.0, 0.88, GrowerAction.CHECK_SPACING),  # touching the next channel only
		(0.5, 0.9, GrowerAction.EXPAND_CHANNEL),  # along at the threshold wins over across
		(0.44, 0.33, GrowerAction.EXPAND_CHANNEL),  # both under 0.5 (smoothing): the larger decides
		(0.33, 0.44, GrowerAction.CHECK_SPACING),
		(0.4, 0.4, GrowerAction.EXPAND_CHANNEL),  # a tie goes to the channel
		(None, 0.6, GrowerAction.CHECK_SPACING),  # NULL counts as 0
		(None, None, GrowerAction.EXPAND_CHANNEL),
	],
)
def test_grower_action_for_holes(along, across, expected):
	assert grower_action(observation(along=along, across=across)) is expected


def test_grower_action_for_zones():
	zone = observation(hole_id="L1-C1-Z-dense_far", kind=ObservationKind.ZONE, along=None, across=None)
	assert grower_action(zone) is GrowerAction.CHECK_CANOPY


def test_camera_readiness_orders_counts_and_rounds():
	frame = [
		observation("L1-C2-Z-canopy_far", kind=ObservationKind.ZONE, along=None, across=None),
		observation("L1-C2-R06-H03", along=0.0, across=0.6667000055313110),
		observation("L1-C2-R02-H01", along=0.7778000235557556, across=0.4444000124931335),
		observation("L1-C2-R01-H05", along=0.9, across=0.0),
		observation("L1-C2-R03-H01", status=PlantStatus.CANDIDATE, along=0.9),
		observation("L1-C2-R08-H01", status=PlantStatus.UNCERTAIN),
	]
	result = camera_readiness(frame)

	assert [item.hole_id for item in result.recommendations] == [
		"L1-C2-R01-H05",
		"L1-C2-R02-H01",
		"L1-C2-R06-H03",
		"L1-C2-Z-canopy_far",
	], "expand (by hole id), then check spacing, then canopy; candidate and uncertain are not shown"
	assert [item.action for item in result.recommendations] == [
		GrowerAction.EXPAND_CHANNEL,
		GrowerAction.EXPAND_CHANNEL,
		GrowerAction.CHECK_SPACING,
		GrowerAction.CHECK_CANOPY,
	]
	assert result.recommendations[0].message == MESSAGES[GrowerAction.EXPAND_CHANNEL]
	assert (result.recommendations[1].contact_along, result.recommendations[1].contact_across) == (0.7778, 0.4444)
	assert result.status_counts == {PlantStatus.READY: 4, PlantStatus.CANDIDATE: 1, PlantStatus.UNCERTAIN: 1}
	assert (result.camera_id, result.period, result.image_id) == (
		"level1_camera2",
		"P3",
		"level1_camera2_20261002_180016.jpg",
	)


def test_summarise():
	assert summarise([]) == NOTHING_TO_DO
	frames = [
		camera_readiness([observation("L1-C2-R01-H01", along=0.9), observation("L1-C2-R01-H02", across=0.9)]),
		camera_readiness([observation("L1-C3-R01-H01", along=0.9, camera_id="level1_camera3")]),
	]
	assert summarise(frames) == "2 plants to expand, 1 plant to check spacing"
	only_growing = camera_readiness([observation(status=PlantStatus.GROWING)])
	assert summarise([only_growing]) == NOTHING_TO_DO


# --- get_plant_readiness with a mocked session ---


def readiness_session(version: str | None, frame_times: dict[str, datetime], rows: list[PlantObservation]):
	version_result, times_result, rows_result = MagicMock(), MagicMock(), MagicMock()
	version_result.scalar_one_or_none.return_value = version
	times_result.tuples.return_value.all.return_value = list(frame_times.items())
	rows_result.scalars.return_value = rows
	session = MagicMock()
	session.execute = AsyncMock(side_effect=[version_result, times_result, rows_result])
	return session


@pytest.mark.asyncio
async def test_get_plant_readiness_latest_frame_per_camera():
	rows = [
		observation("L1-C3-R01-H01", along=0.9, camera_id="level1_camera3"),
		observation("L1-C2-R01-H01", across=0.9),
		observation("L1-C2-R01-H02", status=PlantStatus.GROWING),
	]
	frame_time = datetime(2026, 10, 2, 18, 0, 16)
	session = readiness_session(VERSION, {"level1_camera2": frame_time, "level1_camera3": frame_time}, rows)

	# A timezone on as_of is dropped: frame times are farm local time.
	result = await get_plant_readiness(session, 1, datetime(2026, 10, 2, 18, 1, tzinfo=UTC))

	assert result.as_of == datetime(2026, 10, 2, 18, 1)
	assert result.model_version == VERSION
	assert [camera.camera_id for camera in result.cameras] == ["level1_camera2", "level1_camera3"]
	assert result.summary == "1 plant to expand, 1 plant to check spacing"
	times_query = session.execute.await_args_list[1].args[0].compile(dialect=postgresql.dialect())
	assert "captured_at <=" in str(times_query) and "GROUP BY" in str(times_query)
	assert datetime(2026, 10, 2, 18, 1) in times_query.params.values()


@pytest.mark.asyncio
async def test_get_plant_readiness_no_frames():
	session = readiness_session(VERSION, {}, [])
	result = await get_plant_readiness(session, 1, datetime(2026, 9, 1))
	assert result.cameras == [] and result.model_version is None and result.summary == NOTHING_TO_DO
	assert session.execute.await_count == 2, "no row query when no camera has a frame"

	empty_table = readiness_session(None, {}, [])
	assert (await get_plant_readiness(empty_table)).summary == NOTHING_TO_DO
	assert empty_table.execute.await_count == 1


# --- overlay_path ---


@pytest.mark.asyncio
async def test_overlay_path(tmp_path):
	image_id = "level1_camera2_20261002_180016.jpg"
	overlay = tmp_path / "level1_camera2_P3" / "overlays" / image_id
	overlay.parent.mkdir(parents=True)
	overlay.write_bytes(b"jpeg")
	result = MagicMock()
	result.first.return_value = ("level1_camera2", "P3", image_id)
	session = MagicMock()
	session.execute = AsyncMock(return_value=result)

	assert await overlay_path(session, tmp_path, image_id) == overlay
	result.first.return_value = None
	assert await overlay_path(session, tmp_path, "level1_camera2_20200101_000000.jpg") is None


@pytest.mark.asyncio
async def test_overlay_path_rejects_names_before_querying(tmp_path):
	session = MagicMock()
	session.execute = AsyncMock()
	for name in ["../../pyproject.toml", "level1_camera2_20261002_180016.jpg\x00", "nope.jpg", ""]:
		assert await overlay_path(session, tmp_path, name) is None
	session.execute.assert_not_awaited()
