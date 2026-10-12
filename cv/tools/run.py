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
"""

import argparse
import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

import leafy_cv.hole_map as hole_map_module
import leafy_cv.metrics as metrics_module
from leafy_cv.frames import parse_frame_path, read_image
from leafy_cv.hole_map import ACROSS, ALONG, HoleMap, build_cells, zone_mask
from leafy_cv.metrics import draw_plant_outline, hole_contact, measure_frame, pair_contact
from leafy_cv.plant_filter import PlantFilter, pack_masks, unpack_masks
from leafy_cv.readiness import (
	CANDIDATE,
	EMPTY,
	EMPTY_COVERAGE,
	GROWING,
	READY,
	RULE_VERSION,
	UNCERTAIN,
	flip_rate,
	hole_statuses,
	zone_statuses,
)

DEFAULT_PLANT_FILTER = Path(__file__).resolve().parents[1] / "trained" / "plant_filter.json"
METRICS_VERSION = "metrics-v3"  # v2 (7 Oct): zone closure by point count; v3: a point is plant if any outline is
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


def short_hash(data: bytes) -> str:
	return hashlib.sha256(data).hexdigest()[:8]


def map_hash(hole_map: HoleMap, cells) -> str:
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
	return f"L{hole_map.level}-C{hole_map.camera_id.rsplit('camera', 1)[1]}-Z-{name}"


def pick_frames(index_csv: Path, hole_map: HoleMap) -> list[dict]:
	"""Usable frames in the map's dates and period, oldest first."""
	with open(index_csv, encoding="utf-8") as handle:
		rows = [
			row
			for row in csv.DictReader(handle)
			if row["camera_id"] == hole_map.camera_id
			and row["usable"] == "True"
			and row["captured_at"] >= hole_map.valid_from
			and (hole_map.valid_to is None or row["captured_at"] <= hole_map.valid_to)
		]
	other = [row["file"] for row in rows if row["period"] != hole_map.period]
	if other:
		print(f"  WARNING: {len(other)} frames in the map's dates belong to another period, skipped: {other[:3]}")
	return sorted((row for row in rows if row["period"] == hole_map.period), key=lambda row: row["captured_at"])


def load_cache(path: Path, measured_with: str, hash_: str) -> dict[str, list[dict]]:
	"""Cached measurement rows per frame file, only those made with this model and this map."""
	cache: dict[str, list[dict]] = defaultdict(list)
	if path.exists():
		with open(path, encoding="utf-8") as handle:
			for row in csv.DictReader(handle):
				if row["measured_with"] == measured_with and row["map_hash"] == hash_:
					cache[row["file"]].append(row)
	return cache


def layout_problems(index_csv: Path, frames_root: Path, hole_map: HoleMap, maps_dir: Path) -> tuple[list[str], bool]:
	"""What would make this run's statuses silently out of date: (problems, refuse this map).

	- Frames on disk newer than the frame index, for a map still open (valid_to unset): tray changes among
		them haven't been looked for, so the run is refused until the index is rebuilt
		(tools/build_frame_index.py). A closed map can't get new frames, so it still runs.
	- A later period (new layout or camera move found by the index) with no hole map: its frames are
		never measured with the old map (pick_frames keeps the map's own period), but the newest statuses
		then stop at the change, so it is reported. 8 Oct: the guard before the frames after 3 Oct arrive.
	"""
	with open(index_csv, encoding="utf-8") as handle:
		rows = sorted(
			(r for r in csv.DictReader(handle) if r["camera_id"] == hole_map.camera_id), key=lambda r: r["captured_at"]
		)
	problems: list[str] = []
	last = rows[-1]["captured_at"] if rows else ""
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
	periods: dict[str, list[dict]] = defaultdict(list)
	for row in rows:
		periods[row["period"]].append(row)
	mine = periods.get(hole_map.period, [])
	end = mine[-1]["captured_at"] if mine else hole_map.valid_from
	for period, members in periods.items():
		start = members[0]
		if period == hole_map.period or start["captured_at"] <= end:
			continue
		if not (maps_dir / f"{hole_map.camera_id}_{period}.json").exists():
			problems.append(
				f"{hole_map.camera_id}: layout changed at {start['captured_at']} ({start['status']}, period {period}, "
				f"{len(members)} frames) and there is no hole map {hole_map.camera_id}_{period}.json. Those frames are "
				f"not measured; click a map (tools/click_holes.py) before trusting the newest statuses."
			)
	return problems, refuse


def cache_rows(cache: dict[str, list[dict]]) -> list[dict]:
	"""All cached rows, oldest frame first: also frames outside this run (--limit, frames not found)."""
	return [row for file in sorted(cache) for row in cache[file]]


def pixels_path(out_dir: Path, file: str) -> Path:
	return out_dir / "masks" / f"{file}.npz"


def save_plant_pixels(path: Path, plant_mask: np.ndarray, made_with: str) -> None:
	"""Save a frame's plant pixels stamped with what made them (model, filter, metrics version, map)."""
	np.savez_compressed(path, plant=pack_masks(plant_mask[None])[0], made_with=np.array(made_with))


def plant_pixels_made_with(path: Path) -> str | None:
	"""The stamp of a saved pixel file, or None if it is missing or unstamped (then it is re-measured)."""
	if not path.exists():
		return None
	with np.load(path) as data:
		return str(data["made_with"]) if "made_with" in data.files else None


def load_plant_pixels(path: Path, made_with: str, width: int) -> np.ndarray:
	"""A frame's plant pixels; refuses a file made with other settings rather than mixing versions."""
	with np.load(path) as data:
		stamp = str(data["made_with"]) if "made_with" in data.files else None
		if stamp != made_with:
			raise ValueError(f"{path.name}: plant pixels made with {stamp}, this run uses {made_with}")
		return unpack_masks(data["plant"][None], width)[0]


def draw_frame(image, hole_map, cells, plant_mask, rows_by_id, zone_rows, contacts) -> np.ndarray:
	"""Cells tinted by status, plant pixels outlined, a line between each pair of plants, in the same channel
	and across channels (white = open, red = leaves meet along the whole corridor), numbers per hole
	(coverage / contact, %; contact = the highest over both directions)."""
	out = image.copy()
	tint = out.copy()
	for i, hole in enumerate(hole_map.holes):
		tint[cells.cell(i)] = STATUS_COLOURS[rows_by_id[hole.hole_id]["status"]]
	has_cell = cells.labels >= 0
	out[has_cell] = (0.6 * out[has_cell] + 0.4 * tint[has_cell]).astype(np.uint8)
	for zone in hole_map.zones:
		row = zone_rows[zone.name]
		mask = zone_mask(zone, hole_map.image_size)
		colour = np.array(STATUS_COLOURS[row["status"]])
		out[mask] = (0.75 * out[mask] + 0.25 * colour).astype(np.uint8)
		polygon = np.array(zone.polygon, np.int32)
		cv2.polylines(out, [polygon], True, tuple(int(c) for c in colour), 2)
		text = f"{zone.name}: closure {float(row['coverage']):.0%} {row['status']}"
		anchor = tuple(int(v) for v in polygon.min(axis=0) + (6, 18))
		cv2.putText(out, text, anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
		cv2.putText(out, text, anchor, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
	for (i, j), (closed, lines) in contacts.items():
		share = closed / lines if lines else 0.0
		colour = tuple(int(c) for c in (1 - share) * np.array((255, 255, 255)) + share * np.array((40, 40, 230)))
		a, b = hole_map.holes[i], hole_map.holes[j]
		cv2.line(out, (int(a.x), int(a.y)), (int(b.x), int(b.y)), colour, 2 if share >= 0.5 else 1)
	out = draw_plant_outline(out, plant_mask, (255, 255, 0))
	for hole in hole_map.holes:
		row = rows_by_id[hole.hole_id]
		contact = "-" if row["boundary_contact"] == "" else f"{float(row['boundary_contact']) * 100:.0f}"
		text = f"{float(row['coverage']) * 100:.0f}/{contact}"
		at = (int(hole.x) - 14, int(hole.y) + 4)
		cv2.putText(out, text, at, cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 3)
		cv2.putText(out, text, at, cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
	legend = "coverage/contact %   " + "  ".join(STATUS_COLOURS)
	cv2.rectangle(out, (0, out.shape[0] - 22), (out.shape[1], out.shape[0]), (0, 0, 0), -1)
	cv2.putText(out, legend, (6, out.shape[0] - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
	x = 6 + cv2.getTextSize("coverage/contact %   ", cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)[0][0]
	for name, colour in STATUS_COLOURS.items():
		width = cv2.getTextSize(name, cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)[0][0]
		cv2.line(out, (x, out.shape[0] - 4), (x + width, out.shape[0] - 4), colour, 3)
		x += width + cv2.getTextSize("  ", cv2.FONT_HERSHEY_SIMPLEX, 0.42, 1)[0][0]
	return out


def draw_timeline(ids: list[str], frames: list[dict], status_of: dict[tuple[str, str], str], title: str) -> np.ndarray:
	"""One row per hole/zone, one column per frame, coloured by status; a white line at each new day."""
	cell_w, cell_h, left, top = 6, 12, 130, 40
	image = np.full((top + cell_h * len(ids) + 30, left + cell_w * len(frames) + 10, 3), 255, np.uint8)
	cv2.putText(image, title, (6, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
	for r, ident in enumerate(ids):
		y = top + r * cell_h
		cv2.putText(image, ident, (4, y + cell_h - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 0, 0), 1)
		for c, frame in enumerate(frames):
			colour = STATUS_COLOURS[status_of[(frame["file"], ident)]]
			cv2.rectangle(image, (left + c * cell_w, y), (left + (c + 1) * cell_w - 1, y + cell_h - 2), colour, -1)
	previous = None
	for c, frame in enumerate(frames):
		day = frame["captured_at"][:10]
		if day != previous:
			x = left + c * cell_w
			cv2.line(image, (x - 1, top - 4), (x - 1, top + cell_h * len(ids)), (255, 255, 255), 2)
			cv2.putText(image, day[5:], (x, top - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
			previous = day
	return image


def run_map(args, map_path: Path, plant_filter: PlantFilter, filter_hash: str, segmenter_box: list) -> list[str]:
	"""Measure (or reuse) every usable frame of the map's period and write the outputs; returns problems."""
	hole_map = HoleMap.load(map_path)
	name = f"{hole_map.camera_id}_{hole_map.period}"
	problems, refuse = layout_problems(args.index_csv, args.frames_root, hole_map, map_path.parent)
	for problem in problems:
		print(f"  PROBLEM: {problem}")
	if refuse:
		return problems
	cells = build_cells(hole_map)
	out_dir = args.out_dir / name
	(out_dir / "masks").mkdir(parents=True, exist_ok=True)
	measured_with = f"mobilesam-vit_t|filter-{filter_hash}|{METRICS_VERSION}"
	model_version = f"{measured_with}|{RULE_VERSION}"
	hash_ = map_hash(hole_map, cells)
	pixels_made_with = f"{measured_with}|map-{hash_}"

	frames = pick_frames(args.index_csv, hole_map)
	if args.limit:
		frames = frames[: args.limit]
	missing = [f["file"] for f in frames if not (args.frames_root / hole_map.camera_id / f["file"]).exists()]
	if missing:
		print(f"  WARNING: {len(missing)} frames not found under {args.frames_root}, skipped: {missing[:3]}")
		frames = [f for f in frames if f["file"] not in missing]
	if not frames:
		print(f"{name}: no usable frames found; nothing to do")
		return problems
	cache = load_cache(out_dir / "measurements.csv", measured_with, hash_)
	# a frame is measured again unless its numbers AND its saved plant pixels were made with these settings
	# (8 Oct review: an interrupted run with other settings could leave its pixels under the old numbers)
	todo = [
		f
		for f in frames
		if f["file"] not in cache or plant_pixels_made_with(pixels_path(out_dir, f["file"])) != pixels_made_with
	]
	print(f"{name}: {len(frames)} usable frames, {len(frames) - len(todo)} already measured, {len(todo)} to measure")

	for n, frame in enumerate(todo, start=1):
		if not segmenter_box:
			from leafy_cv.segment import Segmenter

			segmenter_box.append(Segmenter(threads=args.threads))
		image = read_image(args.frames_root / hole_map.camera_id / frame["file"])
		measure = measure_frame(image, hole_map, cells, segmenter_box[0], plant_filter)
		rows = []
		for h in measure.holes:
			rows.append(
				{
					"file": frame["file"],
					"captured_at": frame["captured_at"],
					"measured_with": measured_with,
					"map_hash": hash_,
					"id": h.hole_id,
					"kind": "hole",
					"coverage": f"{h.coverage:.4f}",
					"plant_area_px": h.plant_area_px,
					"outline": h.outline,
					"p_plant": "" if h.p_plant is None else f"{h.p_plant:.3f}",
					"flags": ";".join(h.flags),
					"runtime_ms": measure.runtime_ms,
				}
			)
		for zone_name, closure in measure.zones.items():
			rows.append(
				{
					**{k: "" for k in MEASUREMENT_FIELDS},
					"file": frame["file"],
					"captured_at": frame["captured_at"],
					"measured_with": measured_with,
					"map_hash": hash_,
					"id": zone_id(hole_map, zone_name),
					"kind": "zone",
					"coverage": f"{closure:.4f}",
					"runtime_ms": measure.runtime_ms,
				}
			)
		cache[frame["file"]] = rows
		save_plant_pixels(pixels_path(out_dir, frame["file"]), measure.plant_mask, pixels_made_with)
		print(f"  [{n}/{len(todo)}] {frame['file']}  {measure.runtime_ms / 1000:.1f} s", flush=True)
		# write the cache as we go, so an interrupted run keeps what it measured
		if n % 10 == 0 or n == len(todo):
			write_csv(out_dir / "measurements.csv", MEASUREMENT_FIELDS, cache_rows(cache))

	write_csv(out_dir / "measurements.csv", MEASUREMENT_FIELDS, cache_rows(cache))

	# Per gap pair and frame: closed lines between the two plants, from the saved plant pixels.
	width = hole_map.image_size[0]
	gap_contact = {}
	for frame in frames:
		plant_mask = load_plant_pixels(pixels_path(out_dir, frame["file"]), pixels_made_with, width)
		gap_contact[frame["file"]] = pair_contact(plant_mask, cells)
	write_gaps(out_dir / "gaps.csv", hole_map, cells, frames, gap_contact)

	# Statuses over the whole sequence of usable frames, per hole and per zone.
	by_id: dict[str, list[dict]] = defaultdict(list)
	for frame in frames:
		for row in cache[frame["file"]]:
			by_id[row["id"]].append(row)
	holes = {h.hole_id: (i, h) for i, h in enumerate(hole_map.holes)}
	observations, status_of = [], {}
	for ident, rows in by_id.items():
		if rows[0]["kind"] == "hole":
			i, hole = holes[ident]
			pairs = cells.pairs_of(i)
			contact = [hole_contact(gap_contact[r["file"]], pairs) for r in rows]
			by_direction = {
				d: [hole_contact(gap_contact[r["file"]], cells.pairs_of(i, d)) for r in rows] for d in (ALONG, ACROSS)
			}
			statuses = hole_statuses([float(r["coverage"]) for r in rows], contact, reliable=bool(cells.reliable[i]))
		else:
			contact = [None] * len(rows)
			by_direction = {d: [None] * len(rows) for d in (ALONG, ACROSS)}
			statuses = zone_statuses([float(r["coverage"]) for r in rows])
		for k, (row, status, touch) in enumerate(zip(rows, statuses, contact, strict=True)):
			flags = [f for f in row["flags"].split(";") if f]
			if row["kind"] == "hole":
				if not cells.reliable[i]:
					flags.append("edge_of_frame")
				if hole.estimated:
					flags.append("estimated_position")
				if not pairs:
					flags.append("no_partner")
			else:
				flags.append("zone")
			observations.append(
				{
					"image_id": row["file"],
					"model_version": model_version,
					"camera_id": hole_map.camera_id,
					"captured_at": row["captured_at"],
					"level": hole_map.level,
					"period": hole_map.period,
					"hole_id": ident,
					"kind": row["kind"],
					"row": hole.row if row["kind"] == "hole" else "",
					"col": hole.col if row["kind"] == "hole" else "",
					"in_frame": f"{cells.in_frame[i]:.2f}" if row["kind"] == "hole" else "",
					"occupied": float(row["coverage"]) >= EMPTY_COVERAGE,
					"coverage": row["coverage"],
					"boundary_contact": "" if touch is None else f"{touch:.4f}",
					# this frame's contact per direction (boundary_contact is the higher of the two), so the grower
					# message can say whether plants touch along their channel or across to the next channel
					"contact_along": "" if by_direction[ALONG][k] is None else f"{by_direction[ALONG][k]:.4f}",
					"contact_across": "" if by_direction[ACROSS][k] is None else f"{by_direction[ACROSS][k]:.4f}",
					"plant_area_px": row["plant_area_px"],
					"status": status.status,
					"confirmed_frames": status.confirmed_frames,
					"flags": ";".join(flags),
				}
			)
			status_of[(row["file"], ident)] = status.status
	observations.sort(key=lambda r: (r["captured_at"], r["kind"], r["hole_id"]))
	write_csv(out_dir / "observations.csv", list(observations[0]), observations)

	# Overlays (from the saved plant pixels, so statuses are drawn without rerunning MobileSAM).
	if args.overlays != "none":
		(out_dir / "overlays").mkdir(exist_ok=True)
		by_file: dict[str, list[dict]] = defaultdict(list)
		for row in observations:
			by_file[row["image_id"]].append(row)
		picks = frames if args.overlays == "all" else daily_picks(frames)
		for frame in picks:
			image = read_image(args.frames_root / hole_map.camera_id / frame["file"])
			plant_mask = load_plant_pixels(pixels_path(out_dir, frame["file"]), pixels_made_with, image.shape[1])
			rows = by_file[frame["file"]]
			rows_by_id = {r["hole_id"]: r for r in rows if r["kind"] == "hole"}
			zone_rows = {r["hole_id"].split("-Z-", 1)[1]: r for r in rows if r["kind"] == "zone"}
			overlay = draw_frame(image, hole_map, cells, plant_mask, rows_by_id, zone_rows, gap_contact[frame["file"]])
			cv2.imwrite(str(out_dir / "overlays" / f"{Path(frame['file']).stem}.jpg"), overlay)

	ids = [h.hole_id for h in hole_map.holes] + [zone_id(hole_map, z.name) for z in hole_map.zones]
	timeline = draw_timeline(ids, frames, status_of, f"{name}: status per frame ({model_version})")
	cv2.imwrite(str(out_dir / "timeline.png"), timeline)
	summarise(name, frames, observations, cache)
	return problems


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


def write_gaps(path: Path, hole_map: HoleMap, cells, frames, gap_contact) -> None:
	"""One row per frame x pair of plants (direction "along" = same channel, "across" = next channel): closed
	lines out of all lines."""
	rows = []
	for frame in frames:
		for (i, j), (closed, lines) in gap_contact[frame["file"]].items():
			a, b = hole_map.holes[i], hole_map.holes[j]
			rows.append(
				{
					"image_id": frame["file"],
					"captured_at": frame["captured_at"],
					"direction": cells.pair_direction[(i, j)],
					"channels": "-".join(str(c) for c in sorted((hole_map.channel(a), hole_map.channel(b)))),
					"hole_a": a.hole_id,
					"hole_b": b.hole_id,
					"closed_lines": closed,
					"lines": lines,
					"contact": f"{closed / lines:.3f}" if lines else "",
				}
			)
	write_csv(path, GAP_FIELDS, rows)  # header only when the map has no pairs


def daily_picks(frames: list[dict]) -> list[dict]:
	"""The frame nearest midday of each day, plus the first and last frames."""
	by_day: dict[str, list[dict]] = defaultdict(list)
	for frame in frames:
		by_day[frame["captured_at"][:10]].append(frame)
	picks = {frames[0]["file"]: frames[0], frames[-1]["file"]: frames[-1]}
	for day_frames in by_day.values():
		best = min(day_frames, key=lambda f: abs(datetime.fromisoformat(f["captured_at"]).hour - 12))
		picks[best["file"]] = best
	return sorted(picks.values(), key=lambda f: f["captured_at"])


def summarise(name: str, frames: list[dict], observations: list[dict], cache: dict) -> None:
	last = frames[-1]["file"]
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
		datetime.fromisoformat(frames[-1]["captured_at"]) - datetime.fromisoformat(frames[0]["captured_at"])
	).total_seconds() / 86400
	judged = [h for h, s in statuses.items() if UNCERTAIN not in s]
	rates = [flip_rate(statuses[h], days) for h in judged]
	print(f"  holes/zones that became ready: {len(first_ready)} of {len(statuses)}")
	print(f"  status changes per hole per day: mean {np.mean(rates):.2f}, max {max(rates):.2f}" if rates else "")
	runtimes = [int(rows[0]["runtime_ms"]) for rows in cache.values() if rows and rows[0]["runtime_ms"]]
	if runtimes:
		print(f"  measuring time per frame: mean {np.mean(runtimes) / 1000:.1f} s")


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
	tmp = path.with_suffix(".tmp")
	with open(tmp, "w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
		writer.writeheader()
		writer.writerows(rows)
	tmp.replace(path)


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
	segmenter_box: list = []  # MobileSAM is loaded only if some frame needs measuring
	problems = []
	for map_path in args.hole_map:
		problems += run_map(args, map_path, plant_filter, filter_hash, segmenter_box)
	problems = list(dict.fromkeys(problems))  # several maps of one camera report the same thing once
	if problems:
		print("\nPROBLEMS (the newest statuses may be out of date):")
		for problem in problems:
			print(f"- {problem}")
		sys.exit(1)


if __name__ == "__main__":
	main()
