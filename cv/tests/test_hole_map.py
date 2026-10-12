import json

import numpy as np
import pytest

from leafy_cv.hole_map import (
	ACROSS,
	ALONG,
	CELL_RADIUS_FACTOR,
	GAP_LINES,
	MIN_IN_FRAME,
	HoleMap,
	Zone,
	build_cells,
	camera_number,
	draw_overlay,
	in_frame_share,
	make_hole_id,
	number_holes,
	row_problems,
	zone_mask,
	zone_problems,
)

SPACING = 40


def grid_map(board_polygon=None) -> HoleMap:
	"""3 x 3 holes, 40 px apart, centred in a 200 x 200 image."""
	rows = [[(60 + SPACING * c, 60 + SPACING * r, False) for c in range(3)] for r in range(3)]
	return HoleMap(
		camera_id="level1_camera2",
		level=1,
		period="P1",
		valid_from="2026-09-22T13:00:30",
		valid_to=None,
		image_size=(200, 200),
		reference_file="level1_camera2_20260922_130030.jpg",
		holes=number_holes(1, 2, rows),
		board_polygon=board_polygon,
	)


def test_hole_ids_and_numbering():
	assert make_hole_id(1, 2, 3, 5) == "L1-C2-R03-H05"
	assert camera_number("level1_camera3") == 3
	holes = number_holes(1, 2, [[(90, 10, False), (30, 12, True)], [], [(50, 60, False)]])
	# columns are numbered left to right; empty rows are skipped
	assert [h.hole_id for h in holes] == ["L1-C2-R01-H01", "L1-C2-R01-H02", "L1-C2-R02-H01"]
	assert holes[0].x == 30 and holes[0].estimated is True


def test_save_and_load_round_trip(tmp_path):
	original = grid_map(board_polygon=[(0, 0), (199, 0), (199, 199), (0, 199)])
	path = tmp_path / "map.json"
	original.save(path)
	assert HoleMap.load(path) == original


def test_load_rejects_ids_that_disagree_with_row_and_col(tmp_path):
	path = tmp_path / "map.json"
	grid_map().save(path)
	data = json.loads(path.read_text())
	data["holes"][1]["hole_id"] = "L1-C2-R01-H05"  # renumbered by hand, col left at 2
	path.write_text(json.dumps(data))
	with pytest.raises(ValueError, match="would make L1-C2-R01-H02"):
		HoleMap.load(path)
	data["holes"][1] = dict(data["holes"][0])  # same hole twice
	path.write_text(json.dumps(data))
	with pytest.raises(ValueError, match="appears twice"):
		HoleMap.load(path)


def test_each_dot_lies_in_its_own_cell():
	hole_map = grid_map()
	cells = build_cells(hole_map)
	for i, hole in enumerate(hole_map.holes):
		assert cells.labels[int(hole.y), int(hole.x)] == i


def test_neighbours_are_the_touching_cells_only():
	cells = build_cells(grid_map())
	assert cells.neighbours[4] == {1, 3, 5, 7}  # centre: up, left, right, down (not diagonals)
	assert cells.neighbours[0] == {1, 3}  # corner


def test_edge_cells_are_capped():
	cells = build_cells(grid_map())
	assert cells.labels[0, 0] == -1  # far corner of the image belongs to no hole
	ys, xs = np.nonzero(cells.labels == 0)
	assert np.hypot(xs - 60, ys - 60).max() <= CELL_RADIUS_FACTOR * SPACING + 1


def test_gap_corridors_link_both_directions():
	cells = build_cells(grid_map())  # channel_axis "row": each row is a channel
	corridor = cells.corridors[0]  # top-left hole at (60, 60); same-channel neighbour right, next channel below
	assert corridor[80, 60]  # towards the hole below, in the next channel
	assert corridor[60, 80]  # towards the right neighbour in the same channel: expansion separates them (12 Oct)
	assert not corridor[60, 40]  # outer side, no neighbour there
	assert cells.neighbours[0] == {1, 3} and cells.cross_neighbours[0] == {3} and cells.along_neighbours[0] == {1}
	assert cells.pair_direction[(0, 3)] == ACROSS and cells.pair_direction[(0, 1)] == ALONG
	assert (
		cells.partners(0) == [1, 3] and cells.pairs_of(0, ALONG) == [(0, 1)] and cells.pairs_of(0, ACROSS) == [(0, 3)]
	)
	lines = cells.pair_lines[(0, 3)]
	assert len(lines) == GAP_LINES
	assert all(tuple(line[0]) in {(x, 60) for x in range(40, 81)} and line[-1][1] == 100 for line in lines)
	lines = cells.pair_lines[(0, 1)]
	assert len(lines) == GAP_LINES
	assert all(tuple(line[0]) in {(60, y) for y in range(40, 81)} and line[-1][0] == 100 for line in lines)


def test_same_channel_pairs_join_each_hole_to_the_next_one_in_its_channel():
	cells = build_cells(grid_map())
	along = sorted(p for p, d in cells.pair_direction.items() if d == ALONG)
	assert along == [(0, 1), (1, 2), (3, 4), (4, 5), (6, 7), (7, 8)]  # never across rows, never skipping a hole
	across = sorted(p for p, d in cells.pair_direction.items() if d == ACROSS)
	assert across == [(0, 3), (1, 4), (2, 5), (3, 6), (4, 7), (5, 8)]
	assert list(cells.pair_lines)[: len(across)] == across  # "across" pairs first, as before the correction


def channel_map(positions_per_channel, axis="row") -> HoleMap:
	"""Channels 50 px apart, one hole per position along each. axis "row": channels are rows (positions are x);
	axis "col": channels are columns (positions are y, like camera 3 looking along its channels)."""
	if axis == "row":
		rows = [[(x, 40 + 50 * c, False) for x in xs] for c, xs in enumerate(positions_per_channel)]
	else:
		points = [(40 + 50 * c, y, False) for c, ys in enumerate(positions_per_channel) for y in ys]
		rows = [[p for p in points if p[1] == y] for y in sorted({p[1] for p in points})]  # row 1 = top = farthest
	hole_map = grid_map()
	hole_map.image_size = (400, 400)
	hole_map.channel_axis = axis
	hole_map.holes = number_holes(1, 2, rows)
	return hole_map


def test_a_missing_hole_does_not_pair_the_plants_on_either_side_of_it():
	# x = 160 has no hole: 120 and 200 are not neighbours, every other gap is paired
	hole_map = channel_map([[40, 80, 120, 200, 240, 280], [40, 80, 120, 160, 200, 240, 280]])
	cells = build_cells(hole_map)
	along = {tuple(hole_map.holes[k].x for k in p) for p, d in cells.pair_direction.items() if d == ALONG and p[0] < 6}
	assert along == {(40, 80), (80, 120), (200, 240), (240, 280)}
	# at the end of a channel too: the last gap is twice its only neighbour
	cells = build_cells(channel_map([[40, 80, 120, 200], [40, 80, 120, 160]]))
	assert sum(d == ALONG for p, d in cells.pair_direction.items() if p[1] < 4) == 2


def test_perspective_along_a_column_channel_keeps_every_pair():
	# camera 3: channels are columns running away from the camera; spacing grows towards the camera
	# (camera 3 P4 channel 2, 12 Oct: gaps 23, 23, 37, 41, 67, 97 px; 1.6x the gap before it, but not the one after)
	ys = list(np.cumsum([20, 23, 23, 37, 41, 67, 97]))
	hole_map = channel_map([ys, ys, ys], axis="col")
	cells = build_cells(hole_map)
	along = [p for p, d in cells.pair_direction.items() if d == ALONG]
	assert len(along) == 3 * 6
	for i, j in along:
		a, b = hole_map.holes[i], hole_map.holes[j]
		assert a.col == b.col and abs(a.row - b.row) == 1  # same column = same channel, next position along it
	assert all(
		d == ACROSS for p, d in cells.pair_direction.items() if hole_map.holes[p[0]].row == hole_map.holes[p[1]].row
	)


def test_along_corridors_stay_out_of_a_close_next_channel():
	# rows only 20 px apart across, holes 60 px apart along (camera 2's far rows): the along corridor is
	# 0.8 x 20 = 16 px wide, not 0.8 x 60 = 48 px, so its outer lines don't run through the next row's plants
	hole_map = grid_map()
	hole_map.image_size = (300, 200)
	hole_map.holes = number_holes(1, 2, [[(60 + 60 * c, y, False) for c in range(4)] for y in (80, 100)])
	cells = build_cells(hole_map)
	lines = cells.pair_lines[(0, 1)]
	assert cells.pair_direction[(0, 1)] == ALONG and len(lines) == GAP_LINES
	ys = {int(line[0][1]) for line in lines}
	assert max(ys) - min(ys) == pytest.approx(0.8 * 20, abs=1)
	across = cells.pair_lines[(0, 4)]
	xs = {int(line[0][0]) for line in across}
	assert cells.pair_direction[(0, 4)] == ACROSS and max(xs) - min(xs) == pytest.approx(0.8 * 60, abs=1)


def test_staggered_layout_pairs_with_both_facing_holes():
	# row 2 sits half a hole along from row 1: each row-1 hole faces two row-2 holes
	rows = [[(40 + 40 * c, 60, False) for c in range(4)], [(60 + 40 * c, 95, False) for c in range(3)]]
	hole_map = grid_map()
	hole_map.holes = number_holes(1, 2, rows)
	cells = build_cells(hole_map)
	assert cells.cross_neighbours[1] == {4, 5}  # (80, 60) sits between (60, 95) and (100, 95)


def test_channels_can_be_columns():
	hole_map = grid_map()
	hole_map.channel_axis = "col"  # camera 3 looks along the channels: each column is a channel
	cells = build_cells(hole_map)
	assert cells.cross_neighbours[0] == {1} and cells.along_neighbours[0] == {3}
	assert cells.pair_direction[(0, 1)] == ACROSS and cells.pair_direction[(0, 3)] == ALONG
	assert cells.corridors[0][60, 80] and cells.corridors[0][80, 60]  # across to the right, along downwards


def test_unknown_channel_axis_is_refused():
	with pytest.raises(ValueError):
		HoleMap(**{**grid_map().__dict__, "channel_axis": "diagonal"})


def test_old_maps_without_channel_axis_load_as_rows(tmp_path):
	path = tmp_path / "old.json"
	grid_map().save(path)
	data = json.loads(path.read_text())
	del data["channel_axis"]
	path.write_text(json.dumps(data))
	assert HoleMap.load(path).channel_axis == "row"


def test_board_polygon_clips_cells():
	cells = build_cells(grid_map(board_polygon=[(0, 50), (199, 50), (199, 199), (0, 199)]))
	assert (cells.labels[:50] == -1).all()


def test_needs_at_least_three_holes():
	hole_map = grid_map()
	hole_map.holes = hole_map.holes[:2]
	with pytest.raises(ValueError):
		build_cells(hole_map)


def test_row_check_accepts_curved_rows():
	# a fisheye-curved row: y rises towards both edges
	rows = [[(x, 100 + 0.002 * (x - 350) ** 2, False) for x in range(50, 700, 75)]]
	rows.append([(x, 200 + 0.002 * (x - 350) ** 2, False) for x in range(50, 700, 75)])
	hole_map = grid_map()
	hole_map.holes = number_holes(1, 2, rows)
	assert row_problems(hole_map) == []


def test_row_check_flags_holes_clicked_into_the_wrong_row():
	# 30 Sep: new clicks from three rows all landed in the last row (nearest the camera)
	rows = [
		[(x, 100, False) for x in range(50, 700, 75)],
		[(x, 500, False) for x in range(50, 700, 75)] + [(x + 30, 100 + 50, False) for x in range(50, 700, 150)],
	]
	hole_map = grid_map()
	hole_map.holes = number_holes(1, 2, rows)
	problems = row_problems(hole_map)
	assert len(problems) == 1 and problems[0].startswith("row 2")


def test_row_check_flags_double_clicks():
	hole_map = grid_map()
	hole_map.holes = number_holes(1, 2, [[(60, 60, False), (63, 61, False), (100, 60, False), (140, 60, False)]])
	assert any("clicked twice" in p for p in row_problems(hole_map))


def test_in_frame_share_and_reliable_holes():
	cells = build_cells(grid_map())  # all holes well inside the 200 x 200 frame
	assert (cells.in_frame > 0.99).all() and cells.reliable.all()
	centres = np.array([[100.0, 100.0], [100.0, 0.0], [0.0, 0.0]])
	shares = in_frame_share(centres, np.array([20.0, 20.0, 20.0]), 200, 200)
	assert shares[0] == pytest.approx(1.0)
	assert shares[1] == pytest.approx(0.5, abs=0.03)  # centre on the edge: half the reach outside
	assert shares[2] == pytest.approx(0.25, abs=0.03)  # centre in a corner: a quarter inside


def test_hole_at_the_frame_edge_is_left_out_of_decisions():
	hole_map = grid_map()
	rows = [[(60 + SPACING * c, 60 + SPACING * r, False) for c in range(3)] for r in range(2)]
	rows.append([(60 + SPACING * c, 195, False) for c in range(3)])  # last row 5 px from the bottom
	hole_map.holes = number_holes(1, 2, rows)
	cells = build_cells(hole_map)
	assert cells.reliable[:6].all()
	assert not cells.reliable[6:].any()
	assert (cells.in_frame[6:] < MIN_IN_FRAME).all()


def test_zones_round_trip_and_mask(tmp_path):
	hole_map = grid_map()
	hole_map.zones = [Zone(name="canopy_far", polygon=((0, 0), (199, 0), (199, 30), (0, 30)), note="test")]
	path = tmp_path / "map.json"
	hole_map.save(path)
	loaded = HoleMap.load(path)
	assert loaded == hole_map
	mask = zone_mask(loaded.zones[0], loaded.image_size)
	assert mask[10, 100] and not mask[100, 100]
	assert zone_problems(loaded) == []


def test_old_maps_without_zones_still_load(tmp_path):
	path = tmp_path / "old.json"
	grid_map().save(path)
	data = json.loads(path.read_text())
	del data["zones"]
	path.write_text(json.dumps(data))
	assert HoleMap.load(path).zones == []


def test_zone_problems_are_reported():
	hole_map = grid_map()
	hole_map.zones = [
		Zone(name="Canopy Far", polygon=((0, 0), (50, 0), (50, 50))),
		Zone(name="two_corners", polygon=((0, 0), (50, 0))),
		Zone(name="outside", polygon=((0, 0), (500, 0), (500, 50))),
	]
	problems = " | ".join(zone_problems(hole_map))
	assert "snake_case" in problems and "at least 3 corners" in problems and "outside the frame" in problems


def test_overlay_draws_with_zones_and_left_out_holes():
	hole_map = grid_map()
	hole_map.zones = [Zone(name="canopy_far", polygon=((0, 0), (199, 0), (199, 30), (0, 30)))]
	image = np.zeros((200, 200, 3), np.uint8)
	out = draw_overlay(image, hole_map, build_cells(hole_map))
	assert out.shape == image.shape and out[10, 100].any()  # zone shaded
