import csv
import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "click_holes.py"


@pytest.fixture(scope="module")
def click_holes():
	spec = importlib.util.spec_from_file_location("click_holes", TOOL)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


def write_periods(path: Path) -> None:
	rows = [
		("level1_camera2", "P2", "2026-09-22T13:00:30", "2026-09-30T10:00:27"),
		("level1_camera2", "P3", "2026-09-30T11:00:24", "2026-10-03T15:00:21"),
		("level1_camera3", "P4", "2026-09-30T11:00:26", "2026-10-03T15:00:23"),
	]
	with open(path, "w", newline="", encoding="utf-8") as handle:
		writer = csv.writer(handle)
		writer.writerow(["camera_id", "period", "start", "end"])
		writer.writerows(rows)


def test_closed_period_keeps_its_end(click_holes, tmp_path):
	write_periods(tmp_path / "periods.csv")
	assert click_holes.period_dates(tmp_path / "periods.csv", "level1_camera2", "P2") == (
		"2026-09-22T13:00:30",
		"2026-09-30T10:00:27",
	)


def test_latest_period_stays_open(click_holes, tmp_path):
	# 7 Oct: saving a current-layout map wrote the last frame seen as its end, so newer frames were left out
	write_periods(tmp_path / "periods.csv")
	assert click_holes.period_dates(tmp_path / "periods.csv", "level1_camera2", "P3") == ("2026-09-30T11:00:24", None)
	assert click_holes.period_dates(tmp_path / "periods.csv", "level1_camera3", "P4")[1] is None
