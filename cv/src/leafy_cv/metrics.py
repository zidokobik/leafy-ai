"""Per-hole and per-zone numbers for one frame.

For each hole of the frame's hole map:
1. MobileSAM outlines the plant at the hole centre (touching holes and the holes it faces in the next
   channel as "not this" points) and returns three candidate outlines.
2. The plant filter scores each candidate. We keep the **largest candidate the filter calls plant**,
   unless it is far bigger than the hole's cell (`MAX_OUTLINE_VS_CELL`): then a piece of canopy or
   board was outlined, and we keep the smallest plant candidate instead and flag it. (5 Oct: the
   top-rated outline took in some board for 15% of hole prompts; for most of those, another of the
   three was plain plant.)
3. **Plant pixels** = the union of the kept outlines of all holes. Leaves of a neighbour that hang over
   a cell count for that cell too: that is real crowding.

Numbers per hole:
- `coverage`: share of the hole's cell covered by plant pixels.
- `boundary_contact`: do the leaves meet the leaves of a neighbouring plant, in the same channel or in the
  next channel (both directions since 12 Oct; pairs in hole_map.py)? Along each of the `GAP_LINES` lines
  from this plant's centre to a partner's, the line is *closed* when plant pixels run continuously from one
  plant to the other: no stretch of non-plant (visible board) of `MIN_BOARD_RUN_FACTOR` x their distance or
  more. Per partner: closed lines / lines; the hole's contact is its highest over all its partners (one
  closed gap, in either direction, is enough). 0 = clear board between them everywhere, 1 = leaves meet
  across the whole corridor.
  Why lines and not "how much of the gap is covered": in the oblique views, tall near plants are drawn over
  the gap behind them, so the middle of the gap looks covered while board is still visible between the
  plants (7 Oct, camera 2, 22 Sep: open near-row gaps read 0.27-0.79 "covered" but 0.0-0.2 on lines).
- `plant_area_px`: size of the hole's own kept outline (0 if none).

Per zone: `closure` = share of the zone covered by plant, by point count (the point-intercept method of
canopy cover): MobileSAM is prompted on a grid of points inside the zone (`ZONE_GRID_PX` apart, at most
`ZONE_MAX_POINTS`), and a point counts as plant when the filter calls **any** of its 3 candidate outlines
plant (`point_on_plant`).

Checked 7 Oct on 7 frames (2 per camera + an open-board control), any-outline vs smallest-outline rule:
camera 2 canopy_far 22 Sep 13:00 0.90 vs 0.85, 30 Sep 10:00 (palest canopy, closed) 1.00 vs 0.68; camera 3
dense_right 30 Sep 11:00 0.92 vs 0.86, 3 Oct 12:00 0.94 vs 0.93; camera 1 dense_far 30 Sep 11:00 0.79 vs
0.73, 3 Oct 14:00 0.93 vs 0.88; open-board control (camera 2, 22 Sep, rows 2-3: white board with seedlings)
0.11 vs 0.10. By eye: the points the any-outline rule adds are on (mostly pale or pink) leaves; red points
are on board, the magenta far board, frame corners and the gaps between camera 1's plant columns; no board
point was called plant. Limit: small purple/pink seedlings are sometimes missed (reads slightly low there).
Images: data/checks/zones/ (yellow = plant only under the any-outline rule).

Rejected (7 Oct): the plant filter's 16 px tiles (camera 2 canopy_far fell from 0.91 to 0.48 between 22 and
30 Sep while the canopy stayed closed: pale leaves); the union of the points' outlines (camera 1 dense_far
jumped between 0.58 and 0.98 hour to hour: single-leaf outlines leave gaps between leaves); the smallest
outline's verdict (pale leaves rejected: the closed camera 2 canopy fell to 0.63 by 30 Sep).
Closure counts every gap, including gaps along a channel that expansion doesn't change (camera 1).
"""

import time
from dataclasses import dataclass

import cv2
import numpy as np

from leafy_cv.hole_map import Cells, HoleMap, zone_mask
from leafy_cv.plant_filter import MIN_MASK_PIXELS, ImageLayers, PlantFilter, mask_features
from leafy_cv.segment import PROMPT_BATCH, PointMasks, Segmenter

# A kept outline bigger than this x the hole's cell area is not one plant (canopy piece, board, channel).
# A grown plant spreads over about 1-2.5 cells; 4 leaves room for leaves reaching into neighbours.
MAX_OUTLINE_VS_CELL = 4.0
# Zone closure: grid prompts this many px apart (camera 2 canopy_far: about 60 points) ...
ZONE_GRID_PX = 28
# ... but at most this many per zone (wider spacing for big zones): camera 1's dense_far would need ~290
# points at 28 px, about 30 s per frame on its own; 150 points measure closure to within a percent or so.
ZONE_MAX_POINTS = 150
# A visible stretch of board at least this long (x the two plants' distance, at least MIN_BOARD_RUN_PX) on a
# line between them means the leaves don't meet there. Shorter runs are gaps between leaves of one canopy.
MIN_BOARD_RUN_FACTOR = 0.05
MIN_BOARD_RUN_PX = 3

NO_PLANT_OUTLINE = "no_plant_outline"
OVERSIZED_OUTLINE = "oversized_outline"


@dataclass(frozen=True)
class HoleMeasure:
	hole_id: str
	coverage: float
	boundary_contact: float | None  # None when the hole has no partner line inside the frame
	plant_area_px: int
	outline: int  # index (0-2) of the kept MobileSAM candidate, -1 if none was plant
	p_plant: float | None  # plant filter probability of the kept outline
	flags: tuple[str, ...] = ()


@dataclass
class FrameMeasure:
	holes: list[HoleMeasure]
	zones: dict[str, float]  # zone name -> closure
	plant_mask: np.ndarray  # (height, width) bool: union of the kept outlines
	runtime_ms: int


def choose_outline(result: PointMasks, probabilities: np.ndarray, cell_area: int, threshold: float) -> tuple[int, str]:
	"""Index of the outline to keep (-1 for none) and a flag ("" when nothing to report).

	Prefer the largest candidate that the filter calls plant and that isn't oversized for the cell.
	"""
	areas = result.masks.reshape(len(result.masks), -1).sum(axis=1)
	plant = [k for k in range(len(areas)) if areas[k] >= MIN_MASK_PIXELS and probabilities[k] >= threshold]
	if not plant:
		return -1, NO_PLANT_OUTLINE
	fitting = [k for k in plant if areas[k] <= MAX_OUTLINE_VS_CELL * cell_area]
	if fitting:
		return max(fitting, key=lambda k: areas[k]), ""
	return min(plant, key=lambda k: areas[k]), OVERSIZED_OUTLINE


def score_outlines(image_bgr: np.ndarray, layers: ImageLayers, result: PointMasks, plant_filter: PlantFilter):
	"""P(plant) for each of the three candidates (0 for outlines too small to judge)."""
	scores = np.zeros(len(result.masks))
	for k, mask in enumerate(result.masks):
		if mask.sum() >= MIN_MASK_PIXELS:
			scores[k] = float(plant_filter.probability(mask_features(image_bgr, mask, layers))[0])
	return scores


def zone_points(hole_map: HoleMap) -> dict[str, np.ndarray]:
	"""Grid points (x, y) inside each zone, ZONE_GRID_PX apart (wider for zones that would get more than
	ZONE_MAX_POINTS)."""
	width, height = hole_map.image_size
	points = {}
	for zone in hole_map.zones:
		mask = zone_mask(zone, hole_map.image_size)
		step = max(ZONE_GRID_PX, int(np.ceil(np.sqrt(mask.sum() / ZONE_MAX_POINTS))))
		ys, xs = np.mgrid[step // 2 : height : step, step // 2 : width : step]
		grid = np.stack([xs.ravel(), ys.ravel()], axis=1)
		points[zone.name] = grid[mask[grid[:, 1], grid[:, 0]]].astype(np.float32)
	return points


def point_on_plant(image_bgr: np.ndarray, layers: ImageLayers, result: PointMasks, plant_filter: PlantFilter) -> bool:
	"""A zone grid point counts as plant when the filter calls any of its candidate outlines plant."""
	for mask in result.masks:
		if mask.sum() >= MIN_MASK_PIXELS and plant_filter.is_plant(mask_features(image_bgr, mask, layers))[0]:
			return True
	return False


def zone_closure(
	image_bgr: np.ndarray, layers: ImageLayers, hole_map: HoleMap, segmenter: Segmenter, plant_filter: PlantFilter
) -> dict[str, float]:
	"""Share of each zone's grid points that land on plant (see the module docstring). Needs set_image done."""
	closure = {}
	for name, points in zone_points(hole_map).items():
		if len(points) == 0:
			closure[name] = float("nan")
			continue
		on_plant = 0
		for start in range(0, len(points), PROMPT_BATCH):  # a batch at a time: big zones have many points
			for result in segmenter.predict(points[start : start + PROMPT_BATCH]):
				on_plant += point_on_plant(image_bgr, layers, result, plant_filter)
		closure[name] = on_plant / len(points)
	return closure


def measure_frame(
	image_bgr: np.ndarray, hole_map: HoleMap, cells: Cells, segmenter: Segmenter, plant_filter: PlantFilter
) -> FrameMeasure:
	start = time.perf_counter()
	height, width = image_bgr.shape[:2]
	if (width, height) != tuple(hole_map.image_size):
		raise ValueError(f"frame is {width}x{height} but the hole map is for {hole_map.image_size}")

	points = np.array([(h.x, h.y) for h in hole_map.holes], np.float32)
	negatives = [cells.prompt_negatives(i) for i in range(len(hole_map.holes))]
	segmenter.set_image(image_bgr)
	results = segmenter.predict(points, negatives)

	layers = ImageLayers.of(image_bgr)
	areas = cells.areas()
	chosen, flags, probabilities = [], [], []
	for i, result in enumerate(results):
		scores = score_outlines(image_bgr, layers, result, plant_filter)
		k, flag = choose_outline(result, scores, int(areas[i]), plant_filter.threshold)
		chosen.append(result.masks[k] if k >= 0 else None)
		flags.append((k, flag))
		probabilities.append(float(scores[k]) if k >= 0 else None)

	plant_mask = np.zeros((height, width), bool)
	for outline in chosen:
		if outline is not None:
			if outline.shape != plant_mask.shape:
				raise ValueError(f"MobileSAM outline is {outline.shape}, the frame {plant_mask.shape}")
			plant_mask |= outline

	contacts = pair_contact(plant_mask, cells)
	holes = []
	for i, hole in enumerate(hole_map.holes):
		cell = cells.cell(i)
		k, flag = flags[i]
		holes.append(
			HoleMeasure(
				hole_id=hole.hole_id,
				coverage=float(plant_mask[cell].mean()) if cell.any() else 0.0,
				boundary_contact=hole_contact(contacts, cells.pairs_of(i)),
				plant_area_px=int(chosen[i].sum()) if chosen[i] is not None else 0,
				outline=k,
				p_plant=probabilities[i],
				flags=(flag,) if flag else (),
			)
		)

	zones = zone_closure(image_bgr, layers, hole_map, segmenter, plant_filter)
	runtime_ms = int((time.perf_counter() - start) * 1000)
	return FrameMeasure(holes=holes, zones=zones, plant_mask=plant_mask, runtime_ms=runtime_ms)


def line_closed(on_plant: np.ndarray, min_run: int) -> bool:
	"""True if a line's pixels have no run of non-plant pixels of min_run or longer."""
	off = np.concatenate([[0], (~on_plant).astype(np.int8), [0]])
	starts, ends = np.nonzero(np.diff(off) == 1)[0], np.nonzero(np.diff(off) == -1)[0]
	return bool(len(starts) == 0 or (ends - starts).max() < min_run)


def pair_contact(plant_mask: np.ndarray, cells: Cells) -> dict[tuple[int, int], tuple[int, int]]:
	"""Per pair (i, j), both directions: (closed lines, lines). From the frame's plant pixels only, so it can be
	recomputed from saved masks without MobileSAM."""
	out = {}
	for pair, lines in cells.pair_lines.items():
		if not lines:
			out[pair] = (0, 0)
			continue
		length = len(lines[0]) - 1
		min_run = max(MIN_BOARD_RUN_PX, round(MIN_BOARD_RUN_FACTOR * length))
		closed = sum(line_closed(plant_mask[line[:, 1], line[:, 0]], min_run) for line in lines)
		out[pair] = (closed, len(lines))
	return out


def hole_contact(contacts: dict[tuple[int, int], tuple[int, int]], pairs: list[tuple[int, int]]) -> float | None:
	"""The hole's highest contact with any of the given partners (closed lines / lines of that pair): one
	closed gap, along its channel or to the next channel, is enough. None if no partner line is inside the
	frame."""
	shares = [contacts[pair][0] / contacts[pair][1] for pair in pairs if contacts[pair][1]]
	return max(shares) if shares else None


def draw_plant_outline(image_bgr: np.ndarray, plant_mask: np.ndarray, colour=(255, 255, 255)) -> np.ndarray:
	"""Thin contour of the plant pixels on a copy of the image."""
	out = image_bgr.copy()
	contours, _ = cv2.findContours(plant_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cv2.drawContours(out, contours, -1, colour, 1)
	return out
