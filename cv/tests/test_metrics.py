import cv2
import numpy as np
import pytest

from leafy_cv.hole_map import ACROSS, ALONG, HoleMap, Zone, build_cells, number_holes
from leafy_cv.metrics import (
	NO_PLANT_OUTLINE,
	OVERSIZED_OUTLINE,
	choose_outline,
	hole_contact,
	line_closed,
	measure_frame,
	pair_contact,
	zone_points,
)
from leafy_cv.segment import PointMasks

SIZE = 200


def disk(x, y, r):
	mask = np.zeros((SIZE, SIZE), np.uint8)
	cv2.circle(mask, (int(x), int(y)), int(r), 1, -1)
	return mask > 0


def points_masks(*masks, point=(0.0, 0.0)):
	return PointMasks(point=point, masks=np.stack(masks), scores=np.array([0.9, 0.8, 0.7]))


def test_keeps_the_largest_plant_outline():
	result = points_masks(disk(100, 100, 5), disk(100, 100, 12), disk(100, 100, 20))
	assert choose_outline(result, np.array([0.9, 0.9, 0.2]), cell_area=1000, threshold=0.5) == (1, "")


def test_skips_an_outline_far_bigger_than_the_cell():
	result = points_masks(disk(100, 100, 5), disk(100, 100, 12), disk(100, 100, 60))
	# the 60 px disk is ~11000 px for a 1000 px cell: a canopy piece or the board, not this plant
	assert choose_outline(result, np.array([0.9, 0.9, 0.9]), cell_area=1000, threshold=0.5) == (1, "")


def test_only_oversized_plant_outlines_keeps_the_smallest_and_flags_it():
	result = points_masks(disk(100, 100, 40), disk(100, 100, 50), disk(100, 100, 60))
	assert choose_outline(result, np.array([0.9, 0.9, 0.9]), cell_area=100, threshold=0.5) == (0, OVERSIZED_OUTLINE)


def test_no_plant_outline():
	result = points_masks(disk(100, 100, 5), disk(100, 100, 12), disk(100, 100, 20))
	assert choose_outline(result, np.array([0.1, 0.2, 0.3]), cell_area=1000, threshold=0.5) == (-1, NO_PLANT_OUTLINE)


class FakeSegmenter:
	"""Returns, per prompt, the disks drawn in `plants` around that point (or a tiny dot if none)."""

	def __init__(self, plants):
		self.plants = plants

	def set_image(self, image):
		pass

	def predict(self, points, negatives=None):
		out = []
		for x, y in points:
			radius = self.plants.get((int(x), int(y)), 0)
			plant = disk(x, y, radius) if radius else disk(x, y, 1)
			out.append(points_masks(disk(x, y, 1), plant, plant, point=(x, y)))
		return out


class AlwaysPlant:
	threshold = 0.5

	def probability(self, features):
		return np.array([0.9])


def two_channel_map():
	"""Two rows (channels) of three holes, 40 px apart along a row and 50 px between rows."""
	rows = [[(60 + 40 * c, 70, False) for c in range(3)], [(60 + 40 * c, 120, False) for c in range(3)]]
	return HoleMap(
		camera_id="level1_camera2",
		level=1,
		period="P1",
		valid_from="2026-09-22T13:00:30",
		valid_to=None,
		image_size=(SIZE, SIZE),
		reference_file="x.jpg",
		holes=number_holes(1, 2, rows),
	)


def test_measure_frame_coverage_and_contact():
	hole_map = two_channel_map()
	cells = build_cells(hole_map)
	image = np.full((SIZE, SIZE, 3), 200, np.uint8)
	# R01-H01 (60, 70) and R02-H01 (60, 120), 50 px apart in neighbouring channels, overlap in the middle
	# of their corridor but not at its edges; R01-H03 (140, 70) is small and its partner is empty
	segmenter = FakeSegmenter({(60, 70): 30, (60, 120): 25, (140, 70): 8})
	result = measure_frame(image, hole_map, cells, segmenter, AlwaysPlant())
	by_id = {h.hole_id: h for h in result.holes}
	big, partner = by_id["L1-C2-R01-H01"], by_id["L1-C2-R02-H01"]
	small, empty = by_id["L1-C2-R01-H03"], by_id["L1-C2-R02-H03"]
	assert cells.cross_neighbours[0] == {3}  # straight across only: (100, 120) is a diagonal, not facing
	# 9 lines across a 32 px corridor: the 7 middle ones run through leaves only, the 2 edge ones cross board
	assert big.boundary_contact == partner.boundary_contact == 7 / 9
	assert big.coverage > 0.9
	assert 0.05 < small.coverage < 0.6 and small.boundary_contact == 0.0  # 197 px plant in a ~2300 px cell
	assert empty.coverage < 0.05 and empty.plant_area_px <= 5
	outlines = sum(h.plant_area_px for h in result.holes)
	assert big.plant_area_px <= result.plant_mask.sum() <= outlines  # union of the kept outlines


def test_contact_counts_plants_touching_in_the_same_channel():
	# R01-H01 (60, 70) and R01-H02 (100, 70) touch along their channel, with board between them and row 2
	# (y = 120). Expansion separates them, so the hole is crowded (contact 1), not open (0 with next-channel-only).
	hole_map = two_channel_map()
	cells = build_cells(hole_map)
	plant = np.zeros((SIZE, SIZE), bool)
	plant[48:93, 50:111] = True  # one leaf mass over both plants and their whole along corridor (32 px wide)
	contacts = pair_contact(plant, cells)
	assert contacts[(0, 1)] == (9, 9) and cells.pair_direction[(0, 1)] == ALONG
	assert contacts[(0, 3)] == (0, 9) and cells.pair_direction[(0, 3)] == ACROSS
	assert hole_contact(contacts, cells.pairs_of(0)) == 1.0  # the highest over both directions
	assert hole_contact(contacts, cells.pairs_of(0, ALONG)) == 1.0
	assert hole_contact(contacts, cells.pairs_of(0, ACROSS)) == 0.0
	# and the other way round: touching only the next channel is still crowded
	plant = np.zeros((SIZE, SIZE), bool)
	plant[60:131, 44:77] = True  # R01-H01 to R02-H01 across, board between H01 and H02 along the row
	contacts = pair_contact(plant, cells)
	assert (
		hole_contact(contacts, cells.pairs_of(0, ACROSS)) == 1.0
		and hole_contact(contacts, cells.pairs_of(0, ALONG)) == 0.0
	)
	assert hole_contact(contacts, cells.pairs_of(0)) == 1.0


def test_a_line_is_open_only_for_a_long_enough_stretch_of_board():
	assert line_closed(np.array([1, 1, 0, 0, 1, 1], bool), min_run=3)  # 2 px between leaves: still meeting
	assert not line_closed(np.array([1, 0, 0, 0, 1], bool), min_run=3)  # 3 px of board: open
	assert line_closed(np.ones(5, bool), min_run=3)


def test_zone_points_lie_inside_the_zone():
	hole_map = two_channel_map()
	hole_map.zones = [Zone(name="canopy_far", polygon=((0, 0), (199, 0), (199, 40), (0, 40)))]
	points = zone_points(hole_map)["canopy_far"]
	assert len(points) > 0 and (points[:, 1] <= 40).all()


class PlantIfGreen:
	"""Calls an outline plant when its pixels are mostly green (a stand-in for the trained filter)."""

	threshold = 0.5

	def is_plant(self, features):
		return np.array([features[11] > 0.1])  # exg_mean


def test_zone_closure_is_the_share_of_grid_points_on_plant():
	from leafy_cv.metrics import zone_closure
	from leafy_cv.plant_filter import ImageLayers

	hole_map = two_channel_map()
	hole_map.zones = [Zone(name="canopy_far", polygon=((0, 0), (199, 0), (199, 40), (0, 40)))]
	image = np.full((SIZE, SIZE, 3), 200, np.uint8)
	image[:, :100] = (40, 160, 40)  # left half green (plant), right half grey board
	segmenter = FakeSegmenter({})
	segmenter.predict = lambda points, negatives=None: [
		points_masks(disk(x, y, 4), disk(x, y, 6), disk(x, y, 8), point=(x, y)) for x, y in points
	]
	closure = zone_closure(image, ImageLayers.of(image), hole_map, segmenter, PlantIfGreen())["canopy_far"]
	points = zone_points(hole_map)["canopy_far"]
	assert closure == pytest.approx(np.mean([x < 100 for x, _ in points]), abs=0.05) and 0.3 < closure < 0.7


def test_a_point_is_plant_if_any_of_its_outlines_is():
	# on the palest canopy the smallest outline (one pale leaf) is rejected while a bigger one is plant
	from leafy_cv.metrics import point_on_plant
	from leafy_cv.plant_filter import ImageLayers

	image = np.full((SIZE, SIZE, 3), 200, np.uint8)
	cv2.circle(image, (100, 100), 15, (40, 160, 40), -1)  # a plant; its centre pixel area is pale
	cv2.circle(image, (100, 100), 5, (200, 200, 200), -1)
	layers = ImageLayers.of(image)
	on_plant = points_masks(disk(100, 100, 5), disk(100, 100, 15), disk(100, 100, 15), point=(100, 100))
	assert point_on_plant(image, layers, on_plant, PlantIfGreen())
	board = points_masks(disk(170, 170, 5), disk(170, 170, 8), disk(170, 170, 10), point=(170, 170))
	assert not point_on_plant(image, layers, board, PlantIfGreen())
