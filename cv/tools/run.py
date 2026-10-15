"""Run the CV pipeline on every usable frame of a hole map's period: numbers, statuses, overlays.

Usage (from the cv/ folder, after tools/download_weights.py):
	uv run python tools/run.py --hole-map hole_maps/level1_camera2_P2.json --frames-root E:\\Claude
	uv run python tools/run.py --hole-map hole_maps/level1_camera1_P3.json hole_maps/level1_camera2_P3.json ...

For each map it writes data/runs/<camera>_<period>/:
	observations.csv   one row per frame x hole (and zone), with the plant_observations columns + status
	gaps.csv           one row per frame x pair of plants (same channel "along", next channel "across"): lines where
		leaves meet
	measurements.csv   the raw per-frame numbers. A cache: frames already measured with the same model,
		filter and map are not measured again, so reruns are fast and add no duplicates.
	masks/<frame>.npz  the plant pixels per frame, stamped with the settings that made them (re-measured if they differ)
	overlays/<frame>.jpg  cells coloured by status, plant outlines, coverage/contact per hole
	timeline.png       status of every hole (rows) in every frame (columns)

Frames come from data/frame_index.csv: usable, in the map's valid_from..valid_to, and in the map's
period. About 15-20 s per frame on a laptop CPU (MobileSAM encoder + one prompt per hole + zone grid).

Steps per map (run_map): check the map and the layout -> pick the frames -> measure the frames not measured yet ->
contact per pair of plants from the saved plant pixels -> statuses and observation rows -> overlays, timeline, summary.
"""

import argparse
import csv
import functools
import hashlib
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import cv2
import numpy as np

import leafy_cv.hole_map as hole_map_module
import leafy_cv.metrics as metrics_module
from leafy_cv.csv_files import format_optional, write_csv
from leafy_cv.drawing import FONT, draw_plant_outline, put_outlined_text
from leafy_cv.frame_index import IndexRow, map_frames, read_frame_index
from leafy_cv.frames import parse_frame_path, read_image
from leafy_cv.hole_map import (
	ACROSS,
	ALONG,
	Cells,
	HoleMap,
	build_cells,
	camera_number,
	row_problems,
	zone_mask,
	zone_problems,
)
from leafy_cv.metrics import FrameMeasure, hole_contact, measure_frame, pair_contact
from leafy_cv.plant_filter import DEFAULT_PLANT_FILTER, PlantFilter, pack_masks, unpack_masks
from leafy_cv.readiness import (
	CANDIDATE,
	EMPTY,
	EMPTY_COVERAGE,
	GROWING,
	READY,
	RULE_VERSION,
	UNCERTAIN,
	Status,
	flip_rate,
	hole_statuses,
	zone_statuses,
)

if TYPE_CHECKING:
	from leafy_cv.segment import Segmenter

METRICS_VERSION = "metrics-v3"  # v2: zone closure by point count; v3: a point is plant if any outline is
STATUS_COLOURS = {  # BGR
	EMPTY: (150, 150, 150),
	GROWING: (80, 190, 80),
	CANDIDATE: (0, 190, 255),
	READY: (60, 60, 230),
	UNCERTAIN: (200, 130, 60),
}
MEASUREMENT_FIELDS = [
	"file",
	"captured_at",
	"measured_with",
	"map_hash",
	"id",
	"kind",
	"coverage",
	"plant_area_px",
	"outline",
	"p_plant",
	"flags",
	"runtime_ms",
]
GAP_FIELDS = [
	"image_id",
	"captured_at",
	"direction",
	"channels",
	"hole_a",
	"hole_b",
	"closed_lines",
	"lines",
	"contact",
]

# A row of measurements.csv / observations.csv, keyed by its column names (the CSV files are the contract).
Row = dict
# Per pair of plants (i, j): (closed lines, lines), see metrics.pair_contact.
PairContacts = dict[tuple[int, int], tuple[int, int]]


@dataclass(frozen=True)
class MapRun:
	"""One hole map's run: the map, its cells, where its outputs go, and what its numbers were made with."""

	hole_map: HoleMap
	cells: Cells
	out_dir: Path
	measured_with: str  # model | plant filter | metrics version: cached numbers made otherwise are measured again
	map_hash: str  # map_hash(): changes when the map changes what is measured

	@property
	def name(self) -> str:
		return self.out_dir.name

	@property
	def model_version(self) -> str:
		"""The observations' model_version: what made the numbers plus the readiness rule."""
		return f"{self.measured_with}|{RULE_VERSION}"

	@property
	def pixels_made_with(self) -> str:
		"""The stamp on saved plant pixels: they are only reused with exactly these settings and this map."""
		return f"{self.measured_with}|map-{self.map_hash}"

	def pixels_path(self, file: str) -> Path:
		return self.out_dir / "masks" / f"{file}.npz"


def short_hash(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()[:8]


def map_hash(hole_map: HoleMap, cells: Cells) -> str:
	"""Changes when anything that changes what MobileSAM and the filter measure changes: the holes, zones,
	the prompts' "not this" points, cell sizes, outline and zone-grid settings. Not the notes, and not the
	gap lines (contact is recomputed from the saved plant pixels on every run)."""
	key = {
		"holes": [h.__dict__ for h in hole_map.holes],
		"zones": [{"name": z.name, "polygon": z.polygon} for z in hole_map.zones],
		"image_size": hole_map.image_size,
		"negatives": [cells.prompt_negatives(i) for i in range(len(hole_map.holes))],
		"settings": [
			hole_map_module.CELL_RADIUS_FACTOR,
			metrics_module.MAX_OUTLINE_VS_CELL,
			metrics_module.ZONE_GRID_PX,
			metrics_module.ZONE_MAX_POINTS,
		],
	}
	return short_hash(json.dumps(key, sort_keys=True).encode())


def zone_id(hole_map: HoleMap, name: str) -> str:
	"""Pseudo hole id for a zone, e.g. L1-C2-Z-canopy_far."""
	return f"L{hole_map.level}-C{camera_number(hole_map.camera_id)}-Z-{name}"


def zone_name(zone_hole_id: str) -> str:
	"""The zone name back from its pseudo hole id."""
	return zone_hole_id.split("-Z-", 1)[1]


# --- step 1: is the layout still the one the map was made for?


def layout_problems(index_csv: Path, frames_root: Path, hole_map: HoleMap, maps_dir: Path) -> tuple[list[str], bool]:
	"""What would make this run's statuses silently out of date: (problems, refuse this map).

	- Frames on disk newer than the frame index, for a map still open (valid_to unset): tray changes among
		them haven't been looked for, so the run is refused until the index is rebuilt
		(tools/build_frame_index.py). A closed map can't get new frames, so it still runs.
	- A later period (new layout or camera move found by the index) with no hole map: its frames are
		never measured with the old map (pick_frames keeps the map's own period), but the newest statuses
		then stop at the change, so it is reported.
	"""
	rows = read_frame_index(index_csv, hole_map.camera_id)
	problems: list[str] = []
	last = rows[-1].captured_at if rows else ""
	folder = frames_root / hole_map.camera_id
	newer = sorted(
		frame.captured_at.isoformat()
		for frame in (parse_frame_path(path) for path in folder.glob("*.jpg"))
		if frame is not None and frame.camera_id == hole_map.camera_id and frame.captured_at.isoformat() > last
	)
	refuse = bool(newer) and hole_map.valid_to is None
	if refuse:
		problems.append(
			f"{hole_map.camera_id}: {len(newer)} frames on disk ({newer[0]} to {newer[-1]}) are newer than the frame "
			f"index (last {last or 'none'}). Rebuild it first (tools/build_frame_index.py) so tray changes among "
			f"them are found. Not run."
		)
	periods: dict[str, list[IndexRow]] = defaultdict(list)
	for row in rows:
		periods[row.period].append(row)
	mine = periods.get(hole_map.period, [])
	end = mine[-1].captured_at if mine else hole_map.valid_from
	for period, members in periods.items():
		start = members[0]
		if period == hole_map.period or start.captured_at <= end:
			continue
		if not (maps_dir / f"{hole_map.camera_id}_{period}.json").exists():
			problems.append(
				f"{hole_map.camera_id}: layout changed at {start.captured_at} ({start.status}, period {period}, "
				f"{len(members)} frames) and there is no hole map {hole_map.camera_id}_{period}.json. Those frames are "
				f"not measured; click a map (tools/click_holes.py) before trusting the newest statuses."
			)
	return problems, refuse


def map_problems(hole_map: HoleMap) -> list[str]:
	"""The map's own row and zone checks (as in tools/check_hole_map.py). A map that fails them is not measured: a
	hole clicked twice would get a cell of area 0 and gap lines of length 0, and nothing would say so."""
	return [
		f"{hole_map.camera_id}_{hole_map.period}: {problem}. Fix the map (tools/click_holes.py), check it "
		f"(tools/check_hole_map.py). Not run."
		for problem in row_problems(hole_map) + zone_problems(hole_map)
	]


# --- step 2: which frames


def pick_frames(index_csv: Path, hole_map: HoleMap) -> list[IndexRow]:
	"""Usable frames in the map's dates and period, oldest first."""
	mine, other = map_frames(index_csv, hole_map)
	if other:
		files = [row.file for row in other]
		print(f"  WARNING: {len(files)} frames in the map's dates belong to another period, skipped: {files[:3]}")
	return mine


def select_frames(args: argparse.Namespace, run: MapRun) -> list[IndexRow]:
	"""The map's frames, cut to --limit, without frames missing from --frames-root (reported)."""
	frames = pick_frames(args.index_csv, run.hole_map)
	if args.limit:
		frames = frames[: args.limit]
	folder = args.frames_root / run.hole_map.camera_id
	missing = [f.file for f in frames if not (folder / f.file).exists()]
	if missing:
		print(f"  WARNING: {len(missing)} frames not found under {args.frames_root}, skipped: {missing[:3]}")
		frames = [f for f in frames if f.file not in missing]
	return frames


# --- step 3: measure the frames that aren't measured yet (numbers cached in measurements.csv, pixels in masks/)


def load_cache(path: Path, measured_with: str, hash_: str) -> dict[str, list[Row]]:
	"""Cached measurement rows per frame file, only those made with this model and this map."""
	cache: dict[str, list[Row]] = defaultdict(list)
	if path.exists():
		with open(path, encoding="utf-8") as handle:
			for row in csv.DictReader(handle):
				if row["measured_with"] == measured_with and row["map_hash"] == hash_:
					cache[row["file"]].append(row)
	return cache


def cache_rows(cache: dict[str, list[Row]]) -> list[Row]:
	"""All cached rows, oldest frame first: also frames outside this run (--limit, frames not found)."""
	return [row for file in sorted(cache) for row in cache[file]]


def save_plant_pixels(path: Path, plant_mask: np.ndarray, made_with: str) -> None:
	"""Save a frame's plant pixels stamped with what made them (model, filter, metrics version, map)."""
	np.savez_compressed(path, plant=pack_masks(plant_mask[None])[0], made_with=np.array(made_with))


def _stamp(data) -> str | None:
	return str(data["made_with"]) if "made_with" in data.files else None


def plant_pixels_made_with(path: Path) -> str | None:
	"""The stamp of a saved pixel file, or None if it is missing or unstamped (then it is re-measured)."""
	if not path.exists():
		return None
	with np.load(path) as data:
		return _stamp(data)


def load_plant_pixels(path: Path, made_with: str, width: int) -> np.ndarray:
	"""A frame's plant pixels; refuses a file made with other settings rather than mixing versions."""
	with np.load(path) as data:
		stamp = _stamp(data)
		if stamp != made_with:
			raise ValueError(f"{path.name}: plant pixels made with {stamp}, this run uses {made_with}")
		return unpack_masks(data["plant"][None], width)[0]


def measurement_rows(run: MapRun, frame: IndexRow, measure: FrameMeasure) -> list[Row]:
	"""One measurements.csv row per hole and per zone of a measured frame."""
	common = {
		"file": frame.file,
		"captured_at": frame.captured_at,
		"measured_with": run.measured_with,
		"map_hash": run.map_hash,
		"runtime_ms": measure.runtime_ms,
	}
	holes = [
		{
			**common,
			"id": h.hole_id,
			"kind": "hole",
			"coverage": f"{h.coverage:.4f}",
			"plant_area_px": h.plant_area_px,
			"outline": h.outline,
			"p_plant": format_optional(h.p_plant, ".3f"),
			"flags": ";".join(h.flags),
		}
		for h in measure.holes
	]
	zones = [
		{
			**dict.fromkeys(MEASUREMENT_FIELDS, ""),
			**common,
			"id": zone_id(run.hole_map, name),
			"kind": "zone",
			"coverage": f"{closure:.4f}",
		}
		for name, closure in measure.zones.items()
	]
	return holes + zones


def measure_missing(
	args: argparse.Namespace,
	run: MapRun,
	frames: list[IndexRow],
	plant_filter: PlantFilter,
	get_segmenter: Callable[[], "Segmenter"],
) -> dict[str, list[Row]]:
	"""Measurement rows per frame file: from the cache, measuring (MobileSAM) only the frames not in it."""
	cache_path = run.out_dir / "measurements.csv"
	cache = load_cache(cache_path, run.measured_with, run.map_hash)
	# a frame is measured again unless its numbers AND its saved plant pixels were made with these settings
	# (otherwise an interrupted run with other settings could leave its pixels under the old numbers)
	todo = [
		f
		for f in frames
		if f.file not in cache or plant_pixels_made_with(run.pixels_path(f.file)) != run.pixels_made_with
	]
	print(
		f"{run.name}: {len(frames)} usable frames, {len(frames) - len(todo)} already measured, {len(todo)} to measure"
	)
	for n, frame in enumerate(todo, start=1):
		segmenter = get_segmenter()
		image = read_image(args.frames_root / run.hole_map.camera_id / frame.file)
		measure = measure_frame(image, run.hole_map, run.cells, segmenter, plant_filter)
		cache[frame.file] = measurement_rows(run, frame, measure)
		save_plant_pixels(run.pixels_path(frame.file), measure.plant_mask, run.pixels_made_with)
		print(f"  [{n}/{len(todo)}] {frame.file}  {measure.runtime_ms / 1000:.1f} s", flush=True)
		# write the cache as we go, so an interrupted run keeps what it measured (and once more below, at the end)
		if n % 10 == 0:
			write_csv(cache_path, MEASUREMENT_FIELDS, cache_rows(cache), extrasaction="ignore")
	write_csv(cache_path, MEASUREMENT_FIELDS, cache_rows(cache), extrasaction="ignore")
	return cache


# --- step 4: contact per pair of plants, from the saved plant pixels (no MobileSAM)


def gap_contacts(run: MapRun, frames: list[IndexRow]) -> dict[str, PairContacts]:
	"""Per frame file: closed lines / lines for every pair of plants."""
	width = run.hole_map.image_size[0]
	return {
		frame.file: pair_contact(load_plant_pixels(run.pixels_path(frame.file), run.pixels_made_with, width), run.cells)
		for frame in frames
	}


def write_gaps(path: Path, run: MapRun, frames: list[IndexRow], gap_contact: dict[str, PairContacts]) -> None:
	"""One row per frame x pair of plants (direction "along" = same channel, "across" = next channel): closed
	lines out of all lines."""
	holes = run.hole_map.holes
	rows = []
	for frame in frames:
		for (i, j), (closed, lines) in gap_contact[frame.file].items():
			a, b = holes[i], holes[j]
			rows.append(
				{
					"image_id": frame.file,
					"captured_at": frame.captured_at,
					"direction": run.cells.pair_direction[(i, j)],
					"channels": "-".join(str(c) for c in sorted((run.hole_map.channel(a), run.hole_map.channel(b)))),
					"hole_a": a.hole_id,
					"hole_b": b.hole_id,
					"closed_lines": closed,
					"lines": lines,
					"contact": f"{closed / lines:.3f}" if lines else "",
				}
			)
	write_csv(path, GAP_FIELDS, rows, extrasaction="ignore")  # header only when the map has no pairs


# --- step 5: statuses and observation rows (the plant_observations columns)


def observation(run: MapRun, row: Row, status: Status, flags: list[str], hole_fields: dict, contacts: tuple) -> dict:
	"""One observations.csv row. `hole_fields`: row/col/in_frame ("" for zones); `contacts`: (both directions,
	along, across) for this frame, None where not measured."""
	contact, along, across = contacts
	return {
		"image_id": row["file"],
		"model_version": run.model_version,
		"camera_id": run.hole_map.camera_id,
		"captured_at": row["captured_at"],
		"level": run.hole_map.level,
		"period": run.hole_map.period,
		"hole_id": row["id"],
		"kind": row["kind"],
		**hole_fields,
		"occupied": float(row["coverage"]) >= EMPTY_COVERAGE,
		"coverage": row["coverage"],
		"boundary_contact": format_optional(contact, ".4f"),
		# this frame's contact per direction (boundary_contact is the higher of the two), so the grower
		# message can say whether plants touch along their channel or across to the next channel
		"contact_along": format_optional(along, ".4f"),
		"contact_across": format_optional(across, ".4f"),
		"plant_area_px": row["plant_area_px"],
		"status": status.status,
		"confirmed_frames": status.confirmed_frames,
		"flags": ";".join(flags),
	}


def measured_flags(row: Row) -> list[str]:
	return [f for f in row["flags"].split(";") if f]


def hole_observations(run: MapRun, i: int, rows: list[Row], gap_contact: dict[str, PairContacts]) -> list[dict]:
	"""Observation rows of hole i over its frames (rows: its measurements, oldest first)."""
	hole, cells = run.hole_map.holes[i], run.cells

	def contact(direction: str | None = None) -> list[float | None]:
		return [hole_contact(gap_contact[r["file"]], cells.pairs_of(i, direction)) for r in rows]

	both, along, across = contact(), contact(ALONG), contact(ACROSS)
	statuses = hole_statuses([float(r["coverage"]) for r in rows], both, reliable=bool(cells.reliable[i]))
	extra = [
		flag
		for flag, applies in (
			("edge_of_frame", not cells.reliable[i]),
			("estimated_position", hole.estimated),
			("no_partner", not cells.pairs_of(i)),
		)
		if applies
	]
	hole_fields = {"row": hole.row, "col": hole.col, "in_frame": f"{cells.in_frame[i]:.2f}"}
	return [
		observation(run, row, status, measured_flags(row) + extra, hole_fields, (both[k], along[k], across[k]))
		for k, (row, status) in enumerate(zip(rows, statuses, strict=True))
	]


def zone_observations(run: MapRun, rows: list[Row]) -> list[dict]:
	"""Observation rows of one zone over its frames (closure is in the coverage column)."""
	statuses = zone_statuses([float(r["coverage"]) for r in rows])
	hole_fields = {"row": "", "col": "", "in_frame": ""}
	return [
		observation(run, row, status, [*measured_flags(row), "zone"], hole_fields, (None, None, None))
		for row, status in zip(rows, statuses, strict=True)
	]


def build_observations(
	run: MapRun, frames: list[IndexRow], cache: dict[str, list[Row]], gap_contact: dict[str, PairContacts]
) -> list[dict]:
	"""Statuses over the whole sequence of usable frames, per hole and per zone; rows sorted by time."""
	by_id: dict[str, list[Row]] = defaultdict(list)
	for frame in frames:
		for row in cache[frame.file]:
			by_id[row["id"]].append(row)
	index_of = {h.hole_id: i for i, h in enumerate(run.hole_map.holes)}
	observations = []
	for ident, rows in by_id.items():
		if rows[0]["kind"] == "hole":
			observations += hole_observations(run, index_of[ident], rows, gap_contact)
		else:
			observations += zone_observations(run, rows)
	observations.sort(key=lambda r: (r["captured_at"], r["kind"], r["hole_id"]))
	return observations


# --- step 6: pictures (overlays from the saved plant pixels, so statuses are drawn without rerunning MobileSAM)


def tint_by_status(out: np.ndarray, run: MapRun, rows_by_id: dict[str, dict]) -> None:
	tint = out.copy()
	for i, hole in enumerate(run.hole_map.holes):
		tint[run.cells.cell(i)] = STATUS_COLOURS[rows_by_id[hole.hole_id]["status"]]
	has_cell = run.cells.labels >= 0
	out[has_cell] = (0.6 * out[has_cell] + 0.4 * tint[has_cell]).astype(np.uint8)


def draw_zones(out: np.ndarray, hole_map: HoleMap, zone_rows: dict[str, dict]) -> None:
	for zone in hole_map.zones:
		row = zone_rows[zone.name]
		mask = zone_mask(zone, hole_map.image_size)
		colour = np.array(STATUS_COLOURS[row["status"]])
		out[mask] = (0.75 * out[mask] + 0.25 * colour).astype(np.uint8)
		polygon = np.array(zone.polygon, np.int32)
		cv2.polylines(out, [polygon], True, tuple(int(c) for c in colour), 2)
		text = f"{zone.name}: closure {float(row['coverage']):.0%} {row['status']}"
		put_outlined_text(out, text, tuple(int(v) for v in polygon.min(axis=0) + (6, 18)), 0.45)


def draw_pair_lines(out: np.ndarray, hole_map: HoleMap, contacts: PairContacts) -> None:
	"""A line between each pair of plants: white = open, red = leaves meet along the whole corridor."""
	for (i, j), (closed, lines) in contacts.items():
		share = closed / lines if lines else 0.0
		colour = tuple(int(c) for c in (1 - share) * np.array((255, 255, 255)) + share * np.array((40, 40, 230)))
		a, b = hole_map.holes[i], hole_map.holes[j]
		cv2.line(out, (int(a.x), int(a.y)), (int(b.x), int(b.y)), colour, 2 if share >= 0.5 else 1)


def draw_hole_numbers(out: np.ndarray, hole_map: HoleMap, rows_by_id: dict[str, dict]) -> None:
	"""coverage / contact in % at each hole ("-" where contact can't be measured)."""
	for hole in hole_map.holes:
		row = rows_by_id[hole.hole_id]
		contact = "-" if row["boundary_contact"] == "" else f"{float(row['boundary_contact']) * 100:.0f}"
		put_outlined_text(
			out, f"{float(row['coverage']) * 100:.0f}/{contact}", (int(hole.x) - 14, int(hole.y) + 4), 0.35
		)


def draw_legend(out: np.ndarray) -> None:
	prefix = "coverage/contact %   "
	bottom = out.shape[0]
	cv2.rectangle(out, (0, bottom - 22), (out.shape[1], bottom), (0, 0, 0), -1)
	cv2.putText(out, prefix + "  ".join(STATUS_COLOURS), (6, bottom - 7), FONT, 0.42, (255, 255, 255), 1)
	x = 6 + cv2.getTextSize(prefix, FONT, 0.42, 1)[0][0]
	for name, colour in STATUS_COLOURS.items():
		width = cv2.getTextSize(name, FONT, 0.42, 1)[0][0]
		cv2.line(out, (x, bottom - 4), (x + width, bottom - 4), colour, 3)
		x += width + cv2.getTextSize("  ", FONT, 0.42, 1)[0][0]


def draw_frame(image: np.ndarray, run: MapRun, plant_mask: np.ndarray, rows: list[dict], contacts: PairContacts):
	"""Cells tinted by status, plant pixels outlined, a line between each pair of plants, in the same channel
	and across channels (white = open, red = leaves meet along the whole corridor), numbers per hole
	(coverage / contact, %; contact = the highest over both directions). `rows`: the frame's observations."""
	rows_by_id = {r["hole_id"]: r for r in rows if r["kind"] == "hole"}
	zone_rows = {zone_name(r["hole_id"]): r for r in rows if r["kind"] == "zone"}
	out = image.copy()
	tint_by_status(out, run, rows_by_id)
	draw_zones(out, run.hole_map, zone_rows)
	draw_pair_lines(out, run.hole_map, contacts)
	out = draw_plant_outline(out, plant_mask, (255, 255, 0))
	draw_hole_numbers(out, run.hole_map, rows_by_id)
	draw_legend(out)
	return out


def write_overlays(
	args: argparse.Namespace,
	run: MapRun,
	frames: list[IndexRow],
	observations: list[dict],
	gap_contact: dict[str, PairContacts],
) -> None:
	(run.out_dir / "overlays").mkdir(exist_ok=True)
	by_file: dict[str, list[dict]] = defaultdict(list)
	for row in observations:
		by_file[row["image_id"]].append(row)
	picks = frames if args.overlays == "all" else daily_picks(frames)
	for frame in picks:
		image = read_image(args.frames_root / run.hole_map.camera_id / frame.file)
		plant_mask = load_plant_pixels(run.pixels_path(frame.file), run.pixels_made_with, image.shape[1])
		overlay = draw_frame(image, run, plant_mask, by_file[frame.file], gap_contact[frame.file])
		cv2.imwrite(str(run.out_dir / "overlays" / f"{Path(frame.file).stem}.jpg"), overlay)


def draw_timeline(
	ids: list[str], frames: list[IndexRow], status_of: dict[tuple[str, str], str], title: str
) -> np.ndarray:
	"""One row per hole/zone, one column per frame, coloured by status; a white line at each new day."""
	cell_w, cell_h, left, top = 6, 12, 130, 40
	image = np.full((top + cell_h * len(ids) + 30, left + cell_w * len(frames) + 10, 3), 255, np.uint8)
	cv2.putText(image, title, (6, 24), FONT, 0.5, (0, 0, 0), 1)
	for r, ident in enumerate(ids):
		y = top + r * cell_h
		cv2.putText(image, ident, (4, y + cell_h - 2), FONT, 0.33, (0, 0, 0), 1)
		for c, frame in enumerate(frames):
			colour = STATUS_COLOURS[status_of[(frame.file, ident)]]
			cv2.rectangle(image, (left + c * cell_w, y), (left + (c + 1) * cell_w - 1, y + cell_h - 2), colour, -1)
	previous = None
	for c, frame in enumerate(frames):
		day = frame.captured_at[:10]
		if day != previous:
			x = left + c * cell_w
			cv2.line(image, (x - 1, top - 4), (x - 1, top + cell_h * len(ids)), (255, 255, 255), 2)
			cv2.putText(image, day[5:], (x, top - 6), FONT, 0.3, (0, 0, 0), 1)
			previous = day
	return image


def write_timeline(run: MapRun, frames: list[IndexRow], observations: list[dict]) -> None:
	hole_map = run.hole_map
	ids = [h.hole_id for h in hole_map.holes] + [zone_id(hole_map, z.name) for z in hole_map.zones]
	status_of = {(r["image_id"], r["hole_id"]): r["status"] for r in observations}
	timeline = draw_timeline(ids, frames, status_of, f"{run.name}: status per frame ({run.model_version})")
	cv2.imwrite(str(run.out_dir / "timeline.png"), timeline)


def daily_picks(frames: list[IndexRow]) -> list[IndexRow]:
	"""The frame nearest midday of each day, plus the first and last frames."""
	by_day: dict[str, list[IndexRow]] = defaultdict(list)
	for frame in frames:
		by_day[frame.captured_at[:10]].append(frame)
	picks = {frames[0].file: frames[0], frames[-1].file: frames[-1]}
	for day_frames in by_day.values():
		best = min(day_frames, key=lambda f: abs(datetime.fromisoformat(f.captured_at).hour - 12))
		picks[best.file] = best
	return sorted(picks.values(), key=lambda f: f.captured_at)


def summarise(frames: list[IndexRow], observations: list[dict], cache: dict[str, list[Row]]) -> None:
	last = frames[-1].file
	counts = Counter(r["status"] for r in observations if r["image_id"] == last and r["kind"] == "hole")
	print(f"  last frame {last}: " + ", ".join(f"{k} {v}" for k, v in counts.most_common()))
	for row in observations:
		if row["image_id"] == last and row["kind"] == "zone":
			print(f"  {row['hole_id']}: closure {float(row['coverage']):.0%}, {row['status']}")
	first_ready: dict[str, str] = {}
	statuses: dict[str, list[str]] = defaultdict(list)
	for row in observations:
		statuses[row["hole_id"]].append(row["status"])
		if row["status"] == READY and row["hole_id"] not in first_ready:
			first_ready[row["hole_id"]] = row["captured_at"]
	days = (
		datetime.fromisoformat(frames[-1].captured_at) - datetime.fromisoformat(frames[0].captured_at)
	).total_seconds() / 86400
	judged = [h for h, s in statuses.items() if UNCERTAIN not in s]
	rates = [flip_rate(statuses[h], days) for h in judged]
	print(f"  holes/zones that became ready: {len(first_ready)} of {len(statuses)}")
	print(f"  status changes per hole per day: mean {np.mean(rates):.2f}, max {max(rates):.2f}" if rates else "")
	runtimes = [int(rows[0]["runtime_ms"]) for rows in cache.values() if rows and rows[0]["runtime_ms"]]
	if runtimes:
		print(f"  measuring time per frame: mean {np.mean(runtimes) / 1000:.1f} s")


# --- one map, all steps


def run_map(
	args: argparse.Namespace,
	map_path: Path,
	plant_filter: PlantFilter,
	filter_hash: str,
	get_segmenter: Callable[[], "Segmenter"],
) -> list[str]:
	"""Measure (or reuse) every usable frame of the map's period and write the outputs; returns problems."""
	hole_map = HoleMap.load(map_path)
	problems, refuse = layout_problems(args.index_csv, args.frames_root, hole_map, map_path.parent)
	bad_map = map_problems(hole_map)
	problems += bad_map
	for problem in problems:
		print(f"  PROBLEM: {problem}")
	if refuse or bad_map:
		return problems
	cells = build_cells(hole_map)
	run = MapRun(
		hole_map=hole_map,
		cells=cells,
		out_dir=args.out_dir / f"{hole_map.camera_id}_{hole_map.period}",
		measured_with=f"mobilesam-vit_t|filter-{filter_hash}|{METRICS_VERSION}",
		map_hash=map_hash(hole_map, cells),
	)
	(run.out_dir / "masks").mkdir(parents=True, exist_ok=True)

	frames = select_frames(args, run)
	if not frames:
		print(f"{run.name}: no usable frames found; nothing to do")
		return problems
	cache = measure_missing(args, run, frames, plant_filter, get_segmenter)
	gap_contact = gap_contacts(run, frames)
	write_gaps(run.out_dir / "gaps.csv", run, frames, gap_contact)
	observations = build_observations(run, frames, cache, gap_contact)
	write_csv(run.out_dir / "observations.csv", list(observations[0]), observations, extrasaction="ignore")
	if args.overlays != "none":
		write_overlays(args, run, frames, observations, gap_contact)
	write_timeline(run, frames, observations)
	summarise(frames, observations, cache)
	return problems


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--hole-map", type=Path, nargs="+", required=True)
	parser.add_argument("--frames-root", type=Path, required=True)
	parser.add_argument("--index-csv", type=Path, default=Path("data/frame_index.csv"))
	parser.add_argument("--plant-filter", type=Path, default=DEFAULT_PLANT_FILTER)
	parser.add_argument("--out-dir", type=Path, default=Path("data/runs"))
	parser.add_argument("--overlays", choices=("daily", "all", "none"), default="daily")
	parser.add_argument("--threads", type=int, default=None)
	parser.add_argument("--limit", type=int, default=0, help="only the first N frames (for a quick try)")
	args = parser.parse_args()

	plant_filter = PlantFilter.load(args.plant_filter)
	filter_hash = short_hash(args.plant_filter.read_bytes().replace(b"\r\n", b"\n"))

	@functools.cache
	def get_segmenter() -> "Segmenter":
		"""MobileSAM, loaded the first time a frame needs measuring (a few seconds; needs torch)."""
		from leafy_cv.segment import Segmenter

		return Segmenter(threads=args.threads)

	problems = []
	for map_path in args.hole_map:
		problems += run_map(args, map_path, plant_filter, filter_hash, get_segmenter)
	problems = list(dict.fromkeys(problems))  # several maps of one camera report the same thing once
	if problems:
		print("\nPROBLEMS (the newest statuses may be out of date):")
		for problem in problems:
			print(f"- {problem}")
		sys.exit(1)


if __name__ == "__main__":
	main()
