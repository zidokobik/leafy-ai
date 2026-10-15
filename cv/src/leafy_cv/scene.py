"""Where the plants are in a frame, coarsely, to notice when the layout changes.

The frame is cut into 16 x 16 px tiles and the trained plant filter scores each tile. When
plants are moved, removed or arrive, many tiles switch between plant and not plant.

A tile only counts as changed if the other frame has no plant within one tile of it. Leaf edges
that sway, droop at night or grow a little move by about a tile, so they don't count; whole
plants appearing or disappearing do. (Without this tolerance, the canopy right in front of
camera 1 lifting its leaves overnight looked like a layout change.) About 0.7 s per frame.
"""

import cv2
import numpy as np

from leafy_cv.plant_filter import PlantFilter, mask_features

TILE_PX = 16
SKIP_TOP_PX = 48  # timestamp strip and ceiling; not part of the board


def plant_tiles(image_bgr: np.ndarray, plant_filter: PlantFilter) -> np.ndarray:
	"""(rows, cols) bool: True where a tile looks like plant."""
	height, width = image_bgr.shape[:2]
	whole_tile = np.ones((TILE_PX, TILE_PX), bool)
	rows, cols = height // TILE_PX, width // TILE_PX
	features = [
		mask_features(image_bgr[r * TILE_PX : (r + 1) * TILE_PX, c * TILE_PX : (c + 1) * TILE_PX], whole_tile)
		for r in range(rows)
		for c in range(cols)
	]
	return plant_filter.is_plant(np.array(features)).reshape(rows, cols)


def plant_cover(tiles: np.ndarray) -> float:
	"""Share of the frame (below the top strip) that looks like plant."""
	return float(tiles[SKIP_TOP_PX // TILE_PX :].mean())


def plant_change(before: np.ndarray, after: np.ndarray) -> float:
	"""Share of tiles that became plant with no plant nearby before, or stopped being plant with
	no plant nearby now (one-tile tolerance)."""
	near = np.ones((3, 3), np.uint8)
	before_near = cv2.dilate(before.astype(np.uint8), near).astype(bool)
	after_near = cv2.dilate(after.astype(np.uint8), near).astype(bool)
	changed = (after & ~before_near) | (before & ~after_near)
	return float(changed[SKIP_TOP_PX // TILE_PX :].mean())
