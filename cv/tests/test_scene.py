import numpy as np

from leafy_cv.drift import MAX_PLANT_CHANGE, feature_mask
from leafy_cv.scene import SKIP_TOP_PX, TILE_PX, plant_change, plant_cover

ROWS, COLS = 36, 44  # a 704 x 576 frame in 16 px tiles
TOP = SKIP_TOP_PX // TILE_PX


def board_with_plants(cols: list[int]) -> np.ndarray:
	"""Plant tiles in 4-tile-wide columns starting at the given tile columns."""
	tiles = np.zeros((ROWS, COLS), bool)
	for c in cols:
		tiles[10:30, c : c + 4] = True
	return tiles


def test_same_layout_is_no_change():
	tiles = board_with_plants([2, 12, 22, 32])
	assert plant_change(tiles, tiles) == 0.0


def test_leaves_growing_by_one_tile_do_not_count():
	before = board_with_plants([2, 12, 22, 32])
	after = before.copy()
	after[9:31, 1:7] |= True  # first column grew a tile on every side
	assert plant_change(before, after) == 0.0


def test_plants_moved_to_new_places_count():
	before = board_with_plants([2, 12, 22, 32])
	after = board_with_plants([7, 17, 27, 37])
	assert plant_change(before, after) > MAX_PLANT_CHANGE


def test_plants_arriving_on_an_empty_board_count():
	# Level 2, 30 Sep 11:00
	empty = np.zeros((ROWS, COLS), bool)
	assert plant_change(empty, board_with_plants([10, 20, 30])) > MAX_PLANT_CHANGE


def test_top_strip_is_ignored():
	before = np.zeros((ROWS, COLS), bool)
	after = before.copy()
	after[:TOP] = True  # e.g. ceiling lights
	assert plant_change(before, after) == 0.0
	assert plant_cover(after) == 0.0


def test_feature_mask_uses_only_fixed_parts():
	mask = feature_mask((576, 704), [(0, 40, 90, 140), (650, 40, 704, 230)])
	assert mask[100, 50] and mask[100, 680]
	assert not mask[300, 300]  # the board
	assert not mask[10, 50]  # timestamp strip is always skipped
	whole = feature_mask((576, 704))
	assert whole[300, 300] and not whole[570, 690]  # watermark corner skipped
