"""The labelling rules, tested with a fake camera instead of images.

Each fake frame has a camera position (pixels) and a scene id. Frames in the same scene
align with 300 inliers and a shift equal to their position difference; different scenes
can't be aligned (4 inliers), like the real layout changes in the audit.
"""

from leafy_cv.drift import Alignment
from leafy_cv.frame_index import (
	CAMERA_MOVED,
	OK,
	SCENE_CHANGED,
	TRANSIENT_SHIFT,
	UNCONFIRMED,
	UNSTABLE,
	label_sequence,
	map_frames,
)
from leafy_cv.hole_map import Hole, HoleMap


def run(frames: list[tuple[float, str]]):
	def compare(i: int, j: int) -> Alignment:
		(pos_i, scene_i), (pos_j, scene_j) = frames[i], frames[j]
		if scene_i != scene_j:
			return Alignment(inliers=4)
		return Alignment(inliers=300, shift_px=abs(pos_i - pos_j), rotation_deg=0.0)

	labels = label_sequence(len(frames), compare)
	return [lab.status for lab in labels], [lab.period for lab in labels]


def test_steady_camera_is_one_period():
	statuses, periods = run([(0, "a")] * 5)
	assert statuses == [OK] * 5
	assert periods == [1] * 5


def test_one_off_shift_like_camera1_at_5am():
	statuses, periods = run([(0, "a"), (8, "a"), (0, "a"), (0, "a")])
	assert statuses == [OK, TRANSIENT_SHIFT, OK, OK]
	assert periods == [1, 1, 1, 1]


def test_lasting_bump_like_camera3_on_18_sep():
	statuses, periods = run([(0, "a"), (0, "a"), (22, "a"), (22, "a"), (22, "a")])
	assert statuses == [OK, OK, CAMERA_MOVED, OK, OK]
	assert periods == [1, 1, 2, 2, 2]


def test_layout_change_like_20_to_22_sep():
	statuses, periods = run([(0, "a"), (0, "a"), (0, "b"), (0, "b")])
	assert statuses == [OK, OK, SCENE_CHANGED, OK]
	assert periods == [1, 1, 2, 2]


def test_shift_with_few_matches_is_a_scene_change_not_a_move():
	# Camera 3, 30 Sep 05:00: canopy grew overnight, only 16 leaf matches, 23 px apparent shift.
	def compare(i: int, j: int) -> Alignment:
		if i < 2 <= j:
			return Alignment(inliers=16, shift_px=23.0, rotation_deg=1.5)
		return Alignment(inliers=300, shift_px=0.0, rotation_deg=0.0)

	statuses = [lab.status for lab in label_sequence(4, compare)]
	assert statuses == [OK, OK, SCENE_CHANGED, OK]


def test_change_in_the_last_frame_waits_for_confirmation():
	statuses, _ = run([(0, "a"), (0, "a"), (0, "b")])
	assert statuses == [OK, OK, UNCONFIRMED]


def test_two_different_odd_frames_in_a_row():
	statuses, periods = run([(0, "a"), (0, "b"), (0, "c"), (0, "c")])
	assert statuses == [OK, UNSTABLE, SCENE_CHANGED, OK]
	assert periods == [1, 1, 2, 2]


def test_first_frame_of_the_day_never_becomes_the_reference():
	# Camera 1, 1 Oct: 05:00 shifted 4.9 px (just under the limit), 06:00 back, 7.8 px from 05:00.
	frames = [(0.0, "a"), (0.0, "a"), (4.9, "a"), (-2.9, "a"), (-2.9, "a")]
	first_of_day = [True, True, False, True, True]

	def compare(i: int, j: int) -> Alignment:
		return Alignment(inliers=300, shift_px=abs(frames[i][0] - frames[j][0]), rotation_deg=0.0)

	fixed = label_sequence(len(frames), compare, can_anchor=first_of_day)
	assert [lab.status for lab in fixed] == [OK] * 5
	assert [lab.period for lab in fixed] == [1] * 5
	# the old behaviour, for the record: the 05:00 frame became the reference and faked a move
	old = label_sequence(len(frames), compare)
	assert [lab.status for lab in old] == [OK, OK, OK, CAMERA_MOVED, OK]


def test_plants_moved_with_the_camera_still_is_a_scene_change():
	# Camera 1, 30 Sep 11:00: fixed parts match (no move) but the plants were rearranged.
	def compare(i: int, j: int) -> Alignment:
		change = 0.45 if (i < 2) != (j < 2) else 0.02
		return Alignment(inliers=300, shift_px=1.0, rotation_deg=0.0, plant_change=change)

	labels = label_sequence(4, compare)
	assert [lab.status for lab in labels] == [OK, OK, SCENE_CHANGED, OK]
	assert [lab.period for lab in labels] == [1, 1, 2, 2]
	assert labels[2].plant_change == 0.45


def test_one_hour_of_different_plant_cover_is_a_one_off():
	# e.g. morning light, or someone standing in front of the board
	def compare(i: int, j: int) -> Alignment:
		change = 0.40 if 2 in (i, j) else 0.02
		return Alignment(inliers=300, shift_px=0.5, rotation_deg=0.0, plant_change=change)

	assert [lab.status for lab in label_sequence(4, compare)] == [OK, OK, TRANSIENT_SHIFT, OK]


def test_clear_move_needs_many_fixed_part_matches_and_a_real_shift():
	assert Alignment(inliers=333, shift_px=23.6, rotation_deg=0.0).clear_move
	assert not Alignment(inliers=16, shift_px=23.0, rotation_deg=0.0).clear_move
	assert not Alignment(inliers=300, shift_px=1.0, rotation_deg=0.0, plant_change=0.5).clear_move
	assert not Alignment(inliers=300, shift_px=1.0, rotation_deg=0.0, plant_change=0.5).stable


def test_map_frames_keeps_the_maps_own_period(tmp_path):
	# check_hole_map used to take every usable frame in the map's dates, incl. a later layout's (12 Oct)
	rows = [
		("f3", "2026-10-02T10:00:00", "P2", "True"),
		("f1", "2026-10-01T10:00:00", "P2", "True"),
		("f2", "2026-10-01T11:00:00", "P2", "False"),
		("f4", "2026-10-03T10:00:00", "P3", "True"),
		("g1", "2026-10-01T12:00:00", "P2", "True"),  # another camera
		("f0", "2026-09-30T10:00:00", "P2", "True"),  # before the map's dates
	]
	lines = ["camera_id,file,captured_at,period,usable"]
	for file, at, period, usable in rows:
		camera = "level1_camera3" if file.startswith("g") else "level1_camera2"
		lines.append(f"{camera},{file}.jpg,{at},{period},{usable}")
	(tmp_path / "index.csv").write_text("\n".join(lines) + "\n")
	hole_map = HoleMap(
		"level1_camera2", 1, "P2", "2026-10-01T00:00:00", None, (10, 10), "f1.jpg", [Hole("L1-C2-R01-H01", 1, 1, 1, 1)]
	)
	mine, other = map_frames(tmp_path / "index.csv", hole_map)
	assert [r["file"] for r in mine] == ["f1.jpg", "f3.jpg"]  # usable, own period, in the dates, oldest first
	assert [r["file"] for r in other] == ["f4.jpg"]
