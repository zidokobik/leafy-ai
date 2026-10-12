"""tools/run.py end to end on a tiny made-up map, with a fake measurement in place of MobileSAM.

From the independent review (8 Oct): an interrupted run with other settings must not leave its plant
pixels under the old numbers; --limit must not delete cached rows; a map without pairs must not crash.
"""

import csv
import importlib.util
import types
from pathlib import Path

import cv2
import numpy as np
import pytest

from leafy_cv.hole_map import Hole, HoleMap, make_hole_id
from leafy_cv.metrics import FrameMeasure, HoleMeasure

TOOL = Path(__file__).resolve().parents[1] / "tools" / "run.py"
W, H = 120, 90
FRAMES = 6


@pytest.fixture
def run():
	spec = importlib.util.spec_from_file_location("run_tool", TOOL)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


class Stop(Exception):
	pass


class FakeMeasure:
	"""All plant (full=True) or no plant; counts calls; can stop the run at a given call."""

	def __init__(self, full=True, stop_at=None):
		self.full, self.stop_at, self.calls = full, stop_at, 0

	def __call__(self, image, hole_map, cells, segmenter, plant_filter):
		self.calls += 1
		if self.calls == self.stop_at:
			raise Stop
		holes = [HoleMeasure(h.hole_id, 1.0 if self.full else 0.0, None, 0, 0, 0.9) for h in hole_map.holes]
		return FrameMeasure(holes, {}, np.full((H, W), self.full), 1)


def setup(tmp_path, rows=(1, 2, 3), later=(), cols=(1, 2, 3), row_px=30):
	"""Map P2 + FRAMES frames of P2; `later` adds index rows (captured_at, period, status) after them."""
	holes = [Hole(make_hole_id(1, 2, r, c), 20 + 40 * (c - 1), 15 + row_px * (r - 1), r, c) for r in rows for c in cols]
	hole_map = HoleMap("level1_camera2", 1, "P2", "2026-09-01T00:00:00", None, (W, H), "f0.jpg", holes)
	hole_map.save(tmp_path / "map.json")
	(tmp_path / "frames" / "level1_camera2").mkdir(parents=True)
	index = []
	for k in range(FRAMES):
		cv2.imwrite(str(tmp_path / "frames" / "level1_camera2" / f"f{k}.jpg"), np.zeros((H, W, 3), np.uint8))
		index.append(
			{
				"camera_id": "level1_camera2",
				"file": f"f{k}.jpg",
				"usable": "True",
				"captured_at": f"2026-09-02T0{k}:00:00",
				"period": "P2",
				"status": "ok",
			}
		)
	for captured_at, period, status in later:
		index.append(
			{
				"camera_id": "level1_camera2",
				"file": f"later_{captured_at[11:13]}.jpg",
				"usable": "True",
				"captured_at": captured_at,
				"period": period,
				"status": status,
			}
		)
	with open(tmp_path / "index.csv", "w", newline="") as handle:
		writer = csv.DictWriter(handle, fieldnames=list(index[0]))
		writer.writeheader()
		writer.writerows(index)


def go(run, tmp_path, measure, filter_hash, limit=0):
	run.measure_frame = measure
	args = types.SimpleNamespace(
		index_csv=tmp_path / "index.csv",
		limit=limit,
		frames_root=tmp_path / "frames",
		out_dir=tmp_path / "out",
		threads=1,
		overlays="none",
	)
	return run.run_map(args, tmp_path / "map.json", None, filter_hash, lambda: None)


def read(tmp_path, name):
	with open(tmp_path / "out" / "level1_camera2_P2" / name, encoding="utf-8") as handle:
		return list(csv.DictReader(handle))


def test_an_interrupted_run_with_other_settings_is_measured_again(run, tmp_path):
	setup(tmp_path)
	go(run, tmp_path, FakeMeasure(full=True), "aaaa")
	assert {g["contact"] for g in read(tmp_path, "gaps.csv")} == {"1.000"}
	with pytest.raises(Stop):  # other settings, stopped after saving the pixels of 2 frames
		go(run, tmp_path, FakeMeasure(full=False, stop_at=3), "bbbb")
	again = FakeMeasure(full=True)
	go(run, tmp_path, again, "aaaa")
	assert again.calls == 2  # the 2 frames whose pixels the stopped run replaced, not "0 to measure"
	assert {g["contact"] for g in read(tmp_path, "gaps.csv")} == {"1.000"}  # no pixels of the other run


def test_pixels_made_with_other_settings_are_refused(run, tmp_path):
	path = tmp_path / "f.npz"
	run.save_plant_pixels(path, np.ones((H, W), bool), "settings-a")
	assert run.plant_pixels_made_with(path) == "settings-a"
	assert run.load_plant_pixels(path, "settings-a", W).all()
	with pytest.raises(ValueError):
		run.load_plant_pixels(path, "settings-b", W)
	np.savez_compressed(path, plant=np.zeros(3, np.uint8))  # unstamped (made before 8 Oct)
	assert run.plant_pixels_made_with(path) is None
	assert run.plant_pixels_made_with(tmp_path / "missing.npz") is None


def test_a_limited_run_keeps_the_other_cached_frames(run, tmp_path):
	setup(tmp_path)
	go(run, tmp_path, FakeMeasure(), "aaaa")
	before = read(tmp_path, "measurements.csv")
	go(run, tmp_path, FakeMeasure(), "aaaa", limit=2)
	assert read(tmp_path, "measurements.csv") == before and len(before) == FRAMES * 9


def test_a_map_without_pairs_writes_an_empty_gaps_file(run, tmp_path):
	setup(tmp_path, rows=(1, 3, 5), cols=(2,), row_px=15)  # one hole per channel, no adjacent channels: no pair
	go(run, tmp_path, FakeMeasure(), "aaaa")
	assert read(tmp_path, "gaps.csv") == []
	observations = read(tmp_path, "observations.csv")
	assert {o["status"] for o in observations} == {"uncertain"}
	assert all("no_partner" in o["flags"].split(";") for o in observations)


def test_gaps_and_observations_report_both_directions(run, tmp_path):
	setup(tmp_path)  # 3 channels (rows) of 3 holes
	go(run, tmp_path, FakeMeasure(), "aaaa")
	gaps = read(tmp_path, "gaps.csv")
	directions = [g["direction"] for g in gaps]
	assert directions.count("along") == FRAMES * 6 and directions.count("across") == FRAMES * 6
	assert all(g["channels"].split("-")[0] == g["channels"].split("-")[1] for g in gaps if g["direction"] == "along")
	assert all(g["channels"] in ("1-2", "2-3") for g in gaps if g["direction"] == "across")
	holes = [o for o in read(tmp_path, "observations.csv") if o["kind"] == "hole"]
	assert all(o["contact_along"] == o["contact_across"] == o["boundary_contact"] == "1.0000" for o in holes)
	assert all(o["model_version"].endswith("|rule-v5") for o in holes)


def test_frames_newer_than_the_frame_index_stop_the_run(run, tmp_path):
	setup(tmp_path)
	newer = tmp_path / "frames" / "level1_camera2" / "level1_camera2_20261005_120000.jpg"
	cv2.imwrite(str(newer), np.zeros((H, W, 3), np.uint8))  # arrived, but the index wasn't rebuilt
	measure = FakeMeasure()
	problems = go(run, tmp_path, measure, "aaaa")
	assert len(problems) == 1 and "newer than the frame index" in problems[0] and "2026-10-05T12:00:00" in problems[0]
	assert measure.calls == 0 and not (tmp_path / "out" / "level1_camera2_P2" / "observations.csv").exists()


def test_a_new_layout_without_a_map_is_reported_and_never_measured_with_the_old_map(run, tmp_path):
	later = [("2026-09-03T11:00:00", "P3", "scene_changed"), ("2026-09-03T12:00:00", "P3", "ok")]
	setup(tmp_path, later=later)
	measure = FakeMeasure()
	problems = go(run, tmp_path, measure, "aaaa")
	assert (
		len(problems) == 1
		and "layout changed at 2026-09-03T11:00:00 (scene_changed, period P3, 2 frames)" in problems[0]
	)
	assert measure.calls == FRAMES  # only the map's own period
	assert {o["image_id"] for o in read(tmp_path, "observations.csv")} == {f"f{k}.jpg" for k in range(FRAMES)}
	(tmp_path / "level1_camera2_P3.json").write_text("{}")  # once the new layout has its map: no problem
	assert go(run, tmp_path, FakeMeasure(), "aaaa") == []


def test_a_normal_run_has_no_problems(run, tmp_path):
	setup(tmp_path)
	assert go(run, tmp_path, FakeMeasure(), "aaaa") == []


def test_a_closed_map_still_runs_when_newer_frames_arrive(run, tmp_path):
	setup(tmp_path)
	closed = HoleMap.load(tmp_path / "map.json")
	closed.valid_to = "2026-09-02T23:59:59"
	closed.save(tmp_path / "map.json")
	newer = tmp_path / "frames" / "level1_camera2" / "level1_camera2_20261005_120000.jpg"
	cv2.imwrite(str(newer), np.zeros((H, W, 3), np.uint8))
	measure = FakeMeasure()
	assert go(run, tmp_path, measure, "aaaa") == [] and measure.calls == FRAMES
