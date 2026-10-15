"""Hole maps: where each planting hole is in one camera's view, for one period.

A hole map is a JSON file of clicked hole centres (see `tools/click_holes.py`). From those
centres we build, in pixels of that camera's frames:

- a **cell** per hole: every pixel belongs to its nearest hole (a Voronoi cell), cut off at
  `CELL_RADIUS_FACTOR` x the local hole spacing so holes at the edge don't claim the whole frame.
  Cells shrink with distance exactly like the plants do, so ratios measured inside a cell
  (coverage) can be compared across near and far holes.
- **neighbours**: two holes are neighbours when their cells touch.
- **plant pairs** whose gap is judged for crowding, in both directions: channel expansion separates the
  plants *in the same channel*, and touching the next channel matters too, since plants keep some distance
  from the next channel when they go to Level 2.
  - **same-channel pairs** ("along"): each hole and the next hole along its channel (`same_channel_pairs`).
    A pair is skipped when its gap is far longer than the channel's gaps next to it (a hole missing from
    the map would otherwise pair two plants that aren't neighbours).
  - **cross-channel pairs** ("across"): the nearest hole(s) in each adjacent channel. Holes are often
    much closer along a channel than across, so the capped cells of two channels don't always touch;
    these partners are therefore found by distance, not by touching cells.
  `channel_axis` says which holes share a channel: "row" (cameras 1 and 2 see the channels run
  left-right) or "col" (camera 3 looks along them).
- a **gap corridor** per pair: the area from one plant's centre to its partner's, crossed by `GAP_LINES`
  parallel lines. Across channels it is `CORRIDOR_WIDTH_FACTOR` x the along-channel spacing wide; along a
  channel the same, but never wider than `CORRIDOR_WIDTH_FACTOR` x the distance to the next channel, so its
  outer lines stay out of the next channel's plants (camera 2's far rows are only ~26 px apart across but
  ~70 px along). Crowding is judged along those lines (metrics.py): a line is closed when leaves run
  continuously from one plant to the other, with no visible board between them.
- an **in-frame share** per hole: how much of its cell's reach lies inside the frame. Holes at the
  frame edge (under `MIN_IN_FRAME`) are still measured but left out of readiness and evaluation.

A hole map can also hold **zones**: areas such as a closed canopy where plant bases can't be seen,
measured as a whole (share covered by leaves) instead of per hole.

Rows are numbered by distance from the camera: row 1 is the farthest mapped row.
"""

import json
import re
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from itertools import pairwise
from pathlib import Path

import cv2
import numpy as np

from leafy_cv.drawing import ROW_PALETTE, put_outlined_text

CELL_RADIUS_FACTOR = 0.65  # x local spacing; a square grid's Voronoi corner sits at 0.71
# Gap corridor (crowding) between a plant and its partner: this share of the along-channel spacing wide
# (along a channel: also at most this share of the distance to the next channel), crossed by this many
# parallel lines from one plant centre to the other.
CORRIDOR_WIDTH_FACTOR = 0.8
GAP_LINES = 9


class Direction(StrEnum):
	"""Direction of a pair of plants: in the same channel (expansion separates them) or in adjacent channels."""

	ALONG = "along"
	ACROSS = "across"


ALONG, ACROSS = Direction.ALONG, Direction.ACROSS
# Same-channel pairs: a gap longer than this x every adjacent gap in its channel is skipped (a hole missing
# from the map). Compared with the adjacent gaps, not the channel's median, because perspective makes the
# spacing change along a channel: camera 3's channels run 21-104 px, its nearest gaps 1.5-2.5x the median,
# adjacent gaps differ by up to 1.65x on one side but never on both (on all four maps no real pair is
# skipped). A missing hole doubles a gap against both neighbours.
MAX_ALONG_GAP_VS_ADJACENT = 1.6
# Cross-channel neighbours: in each adjacent channel, the nearest hole plus any other within this factor of
# it that also faces this hole (offset along the channel under FACING_OFFSET x the along-channel spacing),
# so a staggered layout pairs with the two holes it sits between, but a straight one not with diagonals ...
CROSS_NEIGHBOUR_FACTOR = 1.35
FACING_OFFSET = 0.75
# ... and none further than this factor x the hole's own along-channel spacing, so the end of a short row
# doesn't pair with a hole diagonally across the board. Local, because perspective makes near rows wider
# apart than far ones (measured on all four maps: cross / along spacing 0.5-1.9).
MAX_CROSS_VS_ALONG = 2.5
MIN_HOLES = 3
# A row's holes lie on one smooth curve (straight, or bent by the fisheye lens). A hole further
# than this x the row's median spacing from the row's best-fit curve was clicked into the wrong row.
MAX_ROW_OFFSET_FACTOR = 0.35
# Two dots closer than this x local spacing are probably the same hole clicked twice.
MIN_DOT_DISTANCE_FACTOR = 0.3
# A hole whose cell reaches past the frame edge is only partly visible, so its coverage is biased.
# Below this share of its reach inside the frame, it is measured but left out of readiness
# decisions and evaluation (camera 2 P2: row 6 at 56-94%, right-edge holes at 73-80%).
MIN_IN_FRAME = 0.85
IN_FRAME_SAMPLES = 41  # grid points across a disk when measuring its in-frame share
CHANNEL_AXES = ("row", "col")


@dataclass(frozen=True)
class Hole:
	hole_id: str
	x: float
	y: float
	row: int
	col: int
	estimated: bool = False  # centre guessed (e.g. hidden under leaves), not seen


@dataclass(frozen=True)
class Zone:
	"""An area measured as a whole instead of per hole: a closed canopy where plant bases can't be seen.

	Reported as closure (share of the zone covered by leaves), never as per-plant numbers. A zone may
	overlap the cells of the nearest mapped row; the two are separate measurements.
	"""

	name: str  # snake_case, e.g. canopy_far
	polygon: tuple[tuple[int, int], ...]
	kind: str = "canopy"
	note: str = ""


@dataclass
class HoleMap:
	camera_id: str
	level: int
	period: str
	valid_from: str
	valid_to: str | None
	image_size: tuple[int, int]  # (width, height)
	reference_file: str
	holes: list[Hole]
	board_polygon: list[tuple[int, int]] | None = None
	notes: str = ""
	zones: list[Zone] = field(default_factory=list)
	# Which holes share a channel: "row" = holes in the same row (channels run left-right in the view),
	# "col" = holes in the same column (the camera looks along the channels). Maps without it are "row".
	channel_axis: str = "row"

	def __post_init__(self) -> None:
		if self.channel_axis not in CHANNEL_AXES:
			raise ValueError(f"channel_axis must be one of {CHANNEL_AXES}, got {self.channel_axis!r}")

	def channel(self, hole: Hole) -> int:
		"""The channel a hole sits in (its row or its column, depending on channel_axis)."""
		return hole.row if self.channel_axis == "row" else hole.col

	def centres(self, dtype=np.float32) -> np.ndarray:
		"""(n, 2) hole centres (x, y), in the order of `holes`."""
		return np.array([(h.x, h.y) for h in self.holes], dtype=dtype)

	@classmethod
	def load(cls, path: Path) -> "HoleMap":
		data = json.loads(Path(path).read_text(encoding="utf-8"))
		data["holes"] = [Hole(**hole) for hole in data["holes"]]
		data["image_size"] = tuple(data["image_size"])
		if data.get("board_polygon"):
			data["board_polygon"] = [tuple(point) for point in data["board_polygon"]]
		data["zones"] = [
			Zone(**{**zone, "polygon": tuple(tuple(point) for point in zone["polygon"])})
			for zone in data.get("zones", [])
		]
		hole_map = cls(**data)
		hole_map.check_ids()
		return hole_map

	def check_ids(self) -> None:
		"""Hole IDs must be unique and agree with each hole's row and col (a hand-edited map can
		renumber one but not the other; the overlay and the metrics would then disagree)."""
		number = camera_number(self.camera_id)
		seen = set()
		for hole in self.holes:
			expected = make_hole_id(self.level, number, hole.row, hole.col)
			if hole.hole_id != expected:
				raise ValueError(f"{hole.hole_id}: row {hole.row} col {hole.col} would make {expected}")
			if hole.hole_id in seen:
				raise ValueError(f"{hole.hole_id} appears twice")
			seen.add(hole.hole_id)

	def save(self, path: Path) -> None:
		Path(path).parent.mkdir(parents=True, exist_ok=True)
		Path(path).write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")


def camera_number(camera_id: str) -> int:
	"""level1_camera2 -> 2"""
	return int(camera_id.rsplit("camera", 1)[1])


def level_number(camera_id: str) -> int:
	"""level1_camera2 -> 1"""
	return int(camera_id.split("_")[0].removeprefix("level"))


def make_hole_id(level: int, camera: int, row: int, col: int) -> str:
	return f"L{level}-C{camera}-R{row:02d}-H{col:02d}"


def number_holes(level: int, camera: int, rows: list[list[tuple[float, float, bool]]]) -> list[Hole]:
	"""Turn clicked rows of (x, y, estimated) into Holes, numbered left to right within each row.

	Rows are numbered in the order they were clicked, starting at 1: click the row farthest from
	the camera first and the nearest row last.
	"""
	holes = []
	for row_number, row in enumerate((r for r in rows if r), start=1):
		for col_number, (x, y, estimated) in enumerate(sorted(row, key=lambda point: point[0]), start=1):
			holes.append(
				Hole(
					hole_id=make_hole_id(level, camera, row_number, col_number),
					x=round(float(x), 1),
					y=round(float(y), 1),
					row=row_number,
					col=col_number,
					estimated=bool(estimated),
				)
			)
	return holes


def distance_matrix(centres: np.ndarray) -> np.ndarray:
	"""(n, n) distances between the centres (in their own precision), inf on the diagonal."""
	distances = np.linalg.norm(centres[:, None, :] - centres[None, :, :], axis=2)
	np.fill_diagonal(distances, np.inf)
	return distances


def principal_axes(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
	"""The points centred on their mean, and their main directions (PCA; row 0 = the longest)."""
	centred = points - points.mean(axis=0)
	return centred, np.linalg.svd(centred, full_matrices=False)[2]


def unit_and_normal(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
	"""Unit vector from a to b, the unit vector at right angles to it, and the distance."""
	a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
	length = float(np.linalg.norm(b - a))
	u = (b - a) / length
	return u, np.array([-u[1], u[0]]), length


def inside_frame(points: np.ndarray, width: int, height: int) -> np.ndarray:
	"""(n,) bool: which (x, y) points lie inside a width x height frame."""
	return (points[:, 0] >= 0) & (points[:, 0] < width) & (points[:, 1] >= 0) & (points[:, 1] < height)


def polygon_mask(polygon, image_size: tuple[int, int]) -> np.ndarray:
	"""(height, width) bool mask of a polygon's inside."""
	width, height = image_size
	mask = np.zeros((height, width), np.uint8)
	cv2.fillPoly(mask, [np.array(polygon, np.int32)], 1)
	return mask > 0


def two_way(pairs, n: int) -> list[set[int]]:
	"""Per hole, the holes it is paired with, from (i, j) pairs."""
	partners: list[set[int]] = [set() for _ in range(n)]
	for i, j in pairs:
		partners[i].add(j)
		partners[j].add(i)
	return partners


def row_problems(hole_map: HoleMap) -> list[str]:
	"""Rows whose holes don't lie on one smooth curve, and dots that sit on top of each other.

	Each row is fitted with a quadratic along its main direction (found by PCA), so curved
	fisheye rows and rows that run diagonally (camera 3) both pass. Rows under 4 holes are
	only checked for duplicates.
	"""
	problems = []
	centres = hole_map.centres(np.float64)
	if len(centres) >= 2:
		distances = distance_matrix(centres)
		spacing = np.sort(distances, axis=1)[:, : min(2, len(centres) - 1)].mean(axis=1)
		for i, j in zip(*np.nonzero(distances < MIN_DOT_DISTANCE_FACTOR * spacing[:, None]), strict=True):
			if i < j:
				a, b = hole_map.holes[i], hole_map.holes[j]
				problems.append(f"{a.hole_id} and {b.hole_id} are only {distances[i, j]:.0f} px apart (clicked twice?)")

	rows = np.array([h.row for h in hole_map.holes])
	for row in sorted(set(rows.tolist())):
		points = centres[rows == row]
		if len(points) < 4:
			continue
		centred, axes = principal_axes(points)
		along, across = centred @ axes[0], centred @ axes[1]
		curve = np.polyval(np.polyfit(along, across, 2), along)
		row_spacing = np.median(np.diff(np.sort(along)))
		worst = np.abs(across - curve).max()
		if worst > MAX_ROW_OFFSET_FACTOR * row_spacing:
			problems.append(
				f"row {row}: its {len(points)} holes don't lie on one curve (a hole is {worst:.0f} px off, "
				f"spacing {row_spacing:.0f} px); holes from different rows were probably clicked into it"
			)
	return problems


def zone_problems(hole_map: HoleMap) -> list[str]:
	"""Zones that can't be measured: too few corners, corners outside the frame, no area, bad or repeated names."""
	width, height = hole_map.image_size
	problems, seen = [], set()
	for zone in hole_map.zones:
		if not re.fullmatch(r"[a-z0-9_]{1,40}", zone.name):
			problems.append(f"zone '{zone.name}': name must be snake_case (a-z, 0-9, _)")
		if zone.name in seen:
			problems.append(f"zone '{zone.name}': name used twice")
		seen.add(zone.name)
		if len(zone.polygon) < 3:
			problems.append(f"zone '{zone.name}': needs at least 3 corners, has {len(zone.polygon)}")
			continue
		outside = [p for p in zone.polygon if not (0 <= p[0] <= width and 0 <= p[1] <= height)]
		if outside:
			problems.append(f"zone '{zone.name}': corners outside the frame {outside}")
		if zone_mask(zone, hole_map.image_size).sum() == 0:
			problems.append(f"zone '{zone.name}': has no area")
	return problems


@dataclass
class Cells:
	"""Pixel geometry built from a hole map. Index i refers to hole_map.holes[i]."""

	labels: np.ndarray  # (height, width) int32, -1 where no cell
	spacing: np.ndarray  # (n,) local hole spacing in px
	in_frame: np.ndarray  # (n,) share of each hole's full reach (radius disk) inside the frame, 0-1
	neighbours: list[set[int]] = field(default_factory=list)  # holes whose cells touch
	# holes each hole faces in the adjacent channels (one-way: under perspective, A may face B but not B A)
	facing: list[set[int]] = field(default_factory=list)
	cross_neighbours: list[set[int]] = field(default_factory=list)  # facing, made two-way: the "across" pairs
	along_neighbours: list[set[int]] = field(default_factory=list)  # next hole(s) in the same channel: "along"
	corridors: list[np.ndarray] = field(default_factory=list)  # (height, width) bool per hole: its gap corridors
	# per pair (i, j), i < j, in both directions: the GAP_LINES lines across its corridor, each an (n, 2) array
	# of (x, y) pixels from i's centre to j's (lines leaving the frame are dropped). "across" pairs come first.
	pair_lines: dict[tuple[int, int], list[np.ndarray]] = field(default_factory=dict)
	pair_direction: dict[tuple[int, int], Direction] = field(default_factory=dict)  # ALONG or ACROSS per pair

	def pairs_of(self, i: int, direction: Direction | None = None) -> list[tuple[int, int]]:
		"""Hole i's pairs, in both directions (or only ALONG / ACROSS)."""
		return [p for p in self.pair_lines if i in p and (direction is None or self.pair_direction[p] == direction)]

	def partners(self, i: int) -> list[int]:
		"""The holes hole i is paired with, in both directions."""
		return sorted({j for pair in self.pairs_of(i) for j in pair if j != i})

	def prompt_negatives(self, i: int) -> list[int]:
		"""Holes to mark "not this" when outlining hole i: touching cells and the holes it faces."""
		return sorted(self.neighbours[i] | self.facing[i])

	def cell(self, i: int) -> np.ndarray:
		return self.labels == i

	def areas(self) -> np.ndarray:
		return np.bincount(self.labels[self.labels >= 0].ravel(), minlength=len(self.spacing))

	@property
	def reliable(self) -> np.ndarray:
		"""(n,) bool: holes whose cell is mostly inside the frame. Only these feed readiness and evaluation."""
		return self.in_frame >= MIN_IN_FRAME


def in_frame_share(centres: np.ndarray, radii: np.ndarray, width: int, height: int) -> np.ndarray:
	"""Share of each disk (centre, radius) that lies inside a width x height frame."""
	offsets = np.linspace(-1.0, 1.0, IN_FRAME_SAMPLES)
	grid_x, grid_y = np.meshgrid(offsets, offsets)
	inside_disk = grid_x**2 + grid_y**2 <= 1.0
	unit = np.stack([grid_x[inside_disk], grid_y[inside_disk]], axis=1)  # points of a unit disk
	shares = []
	for (cx, cy), radius in zip(centres, radii, strict=True):
		shares.append(inside_frame(unit * radius + (cx, cy), width, height).mean())
	return np.array(shares)


def zone_mask(zone: Zone, image_size: tuple[int, int]) -> np.ndarray:
	"""(height, width) bool mask of a zone's polygon."""
	return polygon_mask(zone.polygon, image_size)


def build_cells(hole_map: HoleMap) -> Cells:
	"""Cells, neighbours, plant pairs in both directions and their gap corridors (see the module docstring)."""
	holes = hole_map.holes
	if len(holes) < MIN_HOLES:
		raise ValueError(f"Need at least {MIN_HOLES} holes to build cells, got {len(holes)}")
	width, height = hole_map.image_size
	centres = hole_map.centres()
	distances = distance_matrix(centres)
	spacing = np.sort(distances, axis=1)[:, :2].mean(axis=1)  # local spacing: mean distance to the 2 nearest holes
	labels = voronoi_labels(centres, spacing, (height, width))
	if hole_map.board_polygon:
		labels[~polygon_mask(hole_map.board_polygon, hole_map.image_size)] = -1

	channels = np.array([hole_map.channel(h) for h in holes])
	distances = distances.astype(np.float64)
	along = along_channel_spacing(channels, distances)
	facing = cross_channel_neighbours(centres, channels, distances, along)
	# a pair is kept if either hole picked the other (the facing rule isn't symmetric under perspective)
	across_pairs = sorted({(min(i, j), max(i, j)) for i in range(len(holes)) for j in facing[i]})
	along_pairs = same_channel_pairs(centres, channels)
	pair_lines, pair_direction, corridors = gap_corridors(
		centres, channels, along, {ACROSS: across_pairs, ALONG: along_pairs}, (height, width)
	)
	return Cells(
		labels=labels,
		spacing=spacing,
		in_frame=in_frame_share(centres, CELL_RADIUS_FACTOR * spacing, width, height),
		neighbours=touching_cells(labels, len(holes)),
		facing=facing,
		cross_neighbours=two_way(across_pairs, len(holes)),
		along_neighbours=two_way(along_pairs, len(holes)),
		corridors=corridors,
		pair_lines=pair_lines,
		pair_direction=pair_direction,
	)


def voronoi_labels(centres: np.ndarray, spacing: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
	"""(height, width) int32: the nearest hole of every pixel, -1 further than CELL_RADIUS_FACTOR x its spacing.
	Computed in row chunks to keep memory small."""
	height, width = shape
	labels = np.empty((height, width), dtype=np.int32)
	xs = np.arange(width, dtype=np.float32)
	for y0 in range(0, height, 64):
		ys = np.arange(y0, min(y0 + 64, height), dtype=np.float32)
		grid_x, grid_y = np.meshgrid(xs, ys)
		d2 = (grid_x[..., None] - centres[:, 0]) ** 2 + (grid_y[..., None] - centres[:, 1]) ** 2
		nearest = d2.argmin(axis=2)
		nearest_d = np.sqrt(np.take_along_axis(d2, nearest[..., None], axis=2)[..., 0])
		nearest[nearest_d > CELL_RADIUS_FACTOR * spacing[nearest]] = -1
		labels[y0 : y0 + len(ys)] = nearest
	return labels


def touching_cells(labels: np.ndarray, n: int) -> list[set[int]]:
	"""Per hole, the holes whose cells touch its cell horizontally or vertically."""
	touching_pairs = set()
	for a, b in ((labels[:, :-1], labels[:, 1:]), (labels[:-1, :], labels[1:, :])):
		touching = (a != b) & (a >= 0) & (b >= 0)
		touching_pairs |= set(zip(a[touching].tolist(), b[touching].tolist(), strict=True))
	return two_way(touching_pairs, n)


def gap_corridors(
	centres: np.ndarray,
	channels: np.ndarray,
	along: np.ndarray,
	pairs: dict[Direction, list[tuple[int, int]]],
	shape: tuple[int, int],
) -> tuple[dict[tuple[int, int], list[np.ndarray]], dict[tuple[int, int], Direction], list[np.ndarray]]:
	"""Per pair: its GAP_LINES lines and its direction ("across" pairs first); per hole: the area of its corridors.

	A corridor is CORRIDOR_WIDTH_FACTOR x the two holes' along-channel spacing wide; along a channel also at most
	CORRIDOR_WIDTH_FACTOR x the distance to the next channel, so its outer lines stay out of that channel's plants."""
	pair_lines, pair_direction = {}, {}
	corridors = [np.zeros(shape, bool) for _ in centres]
	for direction in (ACROSS, ALONG):
		for i, j in pairs[direction]:
			corridor_width = CORRIDOR_WIDTH_FACTOR * np.nanmean([along[i], along[j]])
			if direction == ALONG:
				clearance = next_channel_clearance(centres, channels, i, j)
				corridor_width = min(corridor_width, CORRIDOR_WIDTH_FACTOR * clearance)
			pair_lines[(i, j)] = corridor_lines(centres[i], centres[j], corridor_width, shape)
			pair_direction[(i, j)] = direction
			mask = corridor_mask(centres[i], centres[j], corridor_width, shape)
			corridors[i] |= mask
			corridors[j] |= mask
	return pair_lines, pair_direction, corridors


def same_channel_pairs(centres: np.ndarray, channels: np.ndarray) -> list[tuple[int, int]]:
	"""(i, j), i < j: each hole and the next hole along its channel.

	A channel's holes are ordered by their position along the channel's main direction (PCA), so the order
	doesn't depend on how they were numbered. A gap longer than MAX_ALONG_GAP_VS_ADJACENT x every adjacent gap
	in its channel is skipped: a hole is missing from the map there.
	"""
	pairs = []
	for channel in sorted(set(channels.tolist())):
		members = np.nonzero(channels == channel)[0]
		if len(members) < 2:
			continue
		centred, axes = principal_axes(centres[members].astype(np.float64))
		ordered = members[np.argsort(centred @ axes[0], kind="stable")]
		gaps = [float(np.linalg.norm(centres[b] - centres[a])) for a, b in pairwise(ordered)]
		for k, gap in enumerate(gaps):
			adjacent = gaps[max(0, k - 1) : k] + gaps[k + 1 : k + 2]
			if adjacent and all(gap > MAX_ALONG_GAP_VS_ADJACENT * other for other in adjacent):
				continue
			a, b = int(ordered[k]), int(ordered[k + 1])
			pairs.append((min(a, b), max(a, b)))
	return sorted(pairs)


def next_channel_clearance(centres: np.ndarray, channels: np.ndarray, i: int, j: int) -> float:
	"""Distance from the line between same-channel holes i and j to the nearest hole of another channel that
	sits beside it (its position along the line within a quarter of the gap past either end); inf if none."""
	a = centres[i].astype(np.float64)
	u, v, length = unit_and_normal(a, centres[j])
	clearance = np.inf
	for k in np.nonzero(channels != channels[i])[0]:
		offset = centres[k].astype(np.float64) - a
		if -0.25 * length <= offset @ u <= 1.25 * length:
			clearance = min(clearance, abs(float(offset @ v)))
	return clearance


def cross_channel_neighbours(
	centres: np.ndarray, channels: np.ndarray, distances: np.ndarray, along: np.ndarray
) -> list[set[int]]:
	"""For each hole, the nearest hole(s) in each adjacent channel (channel number +-1).

	Channel numbers are rows or columns, which are numbered in order across the board, so +-1 is the
	channel next to it. `distances`: distance_matrix(centres) (compared in float64, as always); `along`:
	along_channel_spacing.
	"""
	distances = np.asarray(distances, dtype=np.float64)
	cross: list[set[int]] = [set() for _ in centres]
	for i in range(len(centres)):
		direction = channel_direction(centres, channels, distances, i)
		for other in (channels[i] - 1, channels[i] + 1):
			theirs = np.nonzero(channels == other)[0]
			if len(theirs) == 0:
				continue
			nearest_k = int(np.argmin(distances[i, theirs]))
			nearest = distances[i, theirs[nearest_k]]
			if nearest > MAX_CROSS_VS_ALONG * along[i]:
				continue
			cross[i].add(int(theirs[nearest_k]))
			for j in theirs:
				offset = abs(float((centres[j] - centres[i]) @ direction)) if direction is not None else 0.0
				if distances[i, j] <= CROSS_NEIGHBOUR_FACTOR * nearest and offset <= FACING_OFFSET * along[i]:
					cross[i].add(int(j))
	return cross


def channel_direction(centres: np.ndarray, channels: np.ndarray, distances: np.ndarray, i: int) -> np.ndarray | None:
	"""Unit vector along hole i's channel (towards its nearest same-channel hole), None if it is alone."""
	same = np.nonzero((channels == channels[i]) & (np.arange(len(centres)) != i))[0]
	if len(same) == 0:
		return None
	j = same[np.argmin(distances[i, same])]
	vector = (centres[j] - centres[i]).astype(np.float64)
	return vector / np.linalg.norm(vector)


def along_channel_spacing(channels: np.ndarray, distances: np.ndarray) -> np.ndarray:
	"""(n,) distance to the nearest hole in the same channel; for a hole alone in its channel, the
	distance to its nearest hole at all."""
	along = np.empty(len(channels))
	for i in range(len(channels)):
		same = (channels == channels[i]) & (np.arange(len(channels)) != i)
		along[i] = distances[i, same].min() if same.any() else distances[i].min()
	return along


def corridor_mask(a: np.ndarray, b: np.ndarray, corridor_width: float, shape: tuple[int, int]) -> np.ndarray:
	"""(height, width) bool: the rectangle from centre a to centre b, corridor_width wide."""
	a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
	_, normal, _ = unit_and_normal(a, b)
	v = normal * corridor_width / 2
	corners = np.round(np.array([a - v, b - v, b + v, a + v])).astype(np.int32)
	mask = np.zeros(shape, np.uint8)
	cv2.fillPoly(mask, [corners], 1)
	return mask > 0


def corridor_lines(a: np.ndarray, b: np.ndarray, corridor_width: float, shape: tuple[int, int]) -> list[np.ndarray]:
	"""GAP_LINES parallel lines from centre a to centre b, spread across corridor_width, as (n, 2) integer
	(x, y) pixels one px apart. Lines that leave the frame are left out."""
	a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
	_, v, length = unit_and_normal(a, b)
	steps = np.linspace(0.0, 1.0, int(np.ceil(length)) + 1)[:, None]
	height, width = shape
	lines = []
	for offset in np.linspace(-corridor_width / 2, corridor_width / 2, GAP_LINES):
		points = np.round(a + steps * (b - a) + offset * v).astype(np.int64)
		if inside_frame(points, width, height).all():
			lines.append(points)
	return lines


def draw_overlay(image_bgr: np.ndarray, hole_map: HoleMap, cells: Cells) -> np.ndarray:
	"""Zones outlined in white, cells tinted by row, gap corridors darker, centres and short ids on top.

	Holes left out of decisions (mostly outside the frame) get a red ring and a trailing "x".
	"""
	out = image_bgr.copy()
	for zone in hole_map.zones:
		mask = zone_mask(zone, hole_map.image_size)
		out[mask] = (0.7 * out[mask] + 0.3 * np.array((255, 255, 255))).astype(np.uint8)
		polygon = np.array(zone.polygon, np.int32)
		cv2.polylines(out, [polygon], True, (255, 255, 255), 2)
		anchor = tuple(polygon.min(axis=0) + (6, 18))
		put_outlined_text(out, f"zone: {zone.name}", anchor, 0.45)
	tint = out.copy()
	for i, hole in enumerate(hole_map.holes):
		colour = ROW_PALETTE[(hole.row - 1) % len(ROW_PALETTE)]
		cell = cells.cell(i)
		tint[cell] = colour
		tint[cells.corridors[i] & cell] = tuple(int(c * 0.55) for c in colour)
	has_cell = cells.labels >= 0
	out[has_cell] = (0.55 * out[has_cell] + 0.45 * tint[has_cell]).astype(np.uint8)

	edges = np.zeros(cells.labels.shape, np.uint8)
	edges[:, 1:] |= (cells.labels[:, 1:] != cells.labels[:, :-1]).astype(np.uint8)
	edges[1:, :] |= (cells.labels[1:, :] != cells.labels[:-1, :]).astype(np.uint8)
	out[edges > 0] = (255, 255, 255)

	for i, hole in enumerate(hole_map.holes):
		centre = (round(hole.x), round(hole.y))
		cv2.circle(out, centre, 4, (0, 0, 0), -1)
		cv2.circle(out, centre, 3, (0, 255, 255) if not hole.estimated else (0, 140, 255), -1)
		if not cells.reliable[i]:
			cv2.circle(out, centre, 8, (0, 0, 255), 2)
		text = f"R{hole.row}H{hole.col}" + ("" if cells.reliable[i] else " x")
		put_outlined_text(out, text, (centre[0] + 5, centre[1] - 5), 0.35)
	return out
