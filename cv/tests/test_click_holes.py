import csv
import importlib.util
from pathlib import Path

import cv2
import numpy as np
import pytest

from leafy_cv.frames import parse_frame_path
from leafy_cv.hole_map import Hole, HoleMap, level_number

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


def clicker(click_holes, tmp_path):
	frame = parse_frame_path(Path("level1_camera2_20260922_130030.jpg"))
	target = click_holes.MapTarget(frame, "f.jpg", "P2", "2026-09-22T13:00:30", None, tmp_path / "m.json", (400, 300))
	return click_holes.HoleClicker(np.zeros((300, 400, 3), np.uint8), target, 1.0, "row")


def click(c, x, y, button=cv2.EVENT_LBUTTONDOWN):
	c.on_mouse(button, x, y, 0, None)


def test_level_number():
	assert level_number("level1_camera2") == 1 and level_number("level2_camera2") == 2


def test_clicks_go_into_the_current_row_and_save_numbers_them(click_holes, tmp_path):
	c = clicker(click_holes, tmp_path)
	click(c, 100, 50)
	click(c, 40, 50)
	assert c.handle_key(ord("n")) == click_holes.GO
	click(c, 70, 150)
	c.handle_key(ord("s"))
	saved = HoleMap.load(tmp_path / "m.json")
	assert [(h.hole_id, h.x) for h in saved.holes] == [
		("L1-C2-R01-H01", 40),
		("L1-C2-R01-H02", 100),
		("L1-C2-R02-H01", 70),
	]
	assert not c.dirty


def test_undo_removes_the_last_added_hole(click_holes, tmp_path):
	c = clicker(click_holes, tmp_path)
	click(c, 100, 50)
	click(c, 200, 50)
	c.handle_key(ord("u"))
	assert c.rows == [[(100.0, 50.0, False)]]


def test_undo_never_removes_a_hole_loaded_from_the_map(click_holes, tmp_path):
	# 13 Oct: add a hole, right-click it away, press u: the old tool then deleted one of the map's own holes
	c = clicker(click_holes, tmp_path)
	c.load(HoleMap("level1_camera2", 1, "P2", "x", None, (400, 300), "f.jpg", [Hole("L1-C2-R01-H01", 10, 10, 1, 1)]))
	click(c, 300, 200)
	click(c, 300, 200, cv2.EVENT_RBUTTONDOWN)
	c.handle_key(ord("u"))
	assert c.rows == [[(10, 10, False)]]


def test_undo_after_deleting_the_newest_hole_removes_nothing_until_pressed_again(click_holes, tmp_path):
	c = clicker(click_holes, tmp_path)
	click(c, 100, 50)
	c.handle_key(ord("n"))
	click(c, 100, 150)
	click(c, 100, 150, cv2.EVENT_RBUTTONDOWN)  # the newest hole, deleted by hand
	c.handle_key(ord("u"))  # its undo: nothing else goes (nothing removed out of sight in another row)
	assert c.rows == [[(100.0, 50.0, False)], []]
	c.handle_key(ord("u"))  # the hole before it
	assert c.rows == [[], []]


def test_right_click_deletes_the_nearest_hole_and_switches_to_its_row(click_holes, tmp_path):
	c = clicker(click_holes, tmp_path)
	click(c, 100, 50)
	c.handle_key(ord("n"))
	click(c, 100, 150)
	click(c, 105, 55, cv2.EVENT_RBUTTONDOWN)
	assert c.rows == [[], [(100.0, 150.0, False)]] and c.row == 0


def test_a_zone_needs_three_corners_and_keys_wait_while_drawing(click_holes, tmp_path):
	c = clicker(click_holes, tmp_path)
	c.handle_key(ord("z"))
	click(c, 10, 10)
	click(c, 50, 10)
	assert c.handle_key(ord("n")) == click_holes.GO and c.row == 0  # ignored while drawing
	c.handle_key(ord("z"))  # only 2 corners: cancelled
	assert c.zones == [] and c.drawing is None
	c.handle_key(ord("z"))
	for x, y in ((10, 10), (50, 10), (50, 50)):
		click(c, x, y)
	c.handle_key(ord("z"))
	assert [z.name for z in c.zones] == ["canopy_far"] and c.dirty


def test_quit_stays_open_once_when_the_save_finds_problems(click_holes, tmp_path):
	c = clicker(click_holes, tmp_path)
	for x in (10, 11):  # two dots on top of each other: a problem
		click(c, x, 10)
	click(c, 200, 10)
	assert c.handle_key(ord("q")) == click_holes.AGAIN and c.warning
	assert c.handle_key(ord("q")) == click_holes.STOP


def test_x_quits_without_saving(click_holes, tmp_path):
	c = clicker(click_holes, tmp_path)
	click(c, 10, 10)
	assert c.handle_key(ord("x")) == click_holes.STOP and not (tmp_path / "m.json").exists()
