"""Check a hole map: draw its cells on the first, middle and last usable frames of its period.

Usage (from the cv/ folder):
	uv run python tools/check_hole_map.py --hole-map hole_maps/level1_camera2_P2.json --frames-root E:\\Claude

Writes data/checks/hole_maps/<camera>_<period>.jpg and prints the numeric checks, then lists the
holes left out of decisions (mostly outside the frame; drawn with a red ring and "x") and the zones.
Pass when: every cell holds exactly one dot, dots sit on hole centres (or stem bases) in all
three frames, zones cover only the closed canopy, and no check says FAIL.
"""

import argparse
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

from leafy_cv.drawing import put_outlined_text
from leafy_cv.frame_index import map_frames
from leafy_cv.frames import read_image
from leafy_cv.hole_map import (
	ACROSS,
	ALONG,
	GAP_LINES,
	MIN_IN_FRAME,
	Cells,
	HoleMap,
	build_cells,
	draw_overlay,
	row_problems,
	zone_mask,
	zone_problems,
)

# A cell's expected area is about spacing^2 (Voronoi cell of a square grid). Perspective makes near
# cells ~3x bigger than far ones, so compare each cell with its own spacing, not with the median.
MAX_AREA_VS_EXPECTED = 1.6


class Check(NamedTuple):
	name: str
	ok: bool
	detail: str


def map_checks(hole_map: HoleMap, cells: Cells) -> list[Check]:
	"""The six PASS/FAIL checks of a hole map."""
	areas = cells.areas()
	neighbour_counts = np.array([len(n) for n in cells.neighbours])
	vs_expected = areas / cells.spacing**2
	oversized = [h.hole_id for h, r in zip(hole_map.holes, vs_expected, strict=True) if r > MAX_AREA_VS_EXPECTED]
	own_cell = [cells.labels[int(round(h.y)), int(round(h.x))] == i for i, h in enumerate(hole_map.holes)]
	problems = row_problems(hole_map)
	bad_zones = zone_problems(hole_map)
	return [
		Check("every hole has a cell", bool((areas > 0).all()), f"{(areas == 0).sum()} holes without a cell"),
		Check(
			f"no cell over {MAX_AREA_VS_EXPECTED}x its expected size",
			not oversized,
			f"max {vs_expected.max():.2f}x" + (f"; oversized: {', '.join(oversized)}" if oversized else ""),
		),
		Check(
			"every hole has a neighbour",
			bool((neighbour_counts > 0).all()),
			f"counts {sorted(set(neighbour_counts.tolist()))}",
		),
		Check("each dot lies in its own cell", all(own_cell), f"{own_cell.count(False)} dots outside"),
		Check("rows line up, no double clicks", not problems, "; ".join(problems) or "ok"),
		Check("zones are valid", not bad_zones, "; ".join(bad_zones) or f"{len(hole_map.zones)} zones"),
	]


def print_summary(map_name: str, hole_map: HoleMap, cells: Cells, checks: list[Check]) -> None:
	"""Holes, cell sizes, plant pairs per direction, and the checks."""
	areas = cells.areas()
	print(
		f"{map_name}: {len(hole_map.holes)} holes in {max(h.row for h in hole_map.holes)} rows, "
		f"{sum(h.estimated for h in hole_map.holes)} estimated, {len(hole_map.zones)} zones"
	)
	print(f"  cell area px: min {areas.min()}, median {int(np.median(areas))}, max {areas.max()}")
	for direction, label in ((ALONG, "along a channel (same channel)"), (ACROSS, "across channels (next channel)")):
		pairs = [p for p, d in cells.pair_direction.items() if d == direction]
		cut = sum(1 for p in pairs if len(cells.pair_lines[p]) < GAP_LINES)
		print(f"  plant pairs {label}: {len(pairs)} ({cut} partly outside the frame)")
	for check in checks:
		print(f"  {'PASS' if check.ok else 'FAIL'}  {check.name}  ({check.detail})")


def print_left_out(hole_map: HoleMap, cells: Cells) -> None:
	"""Holes left out of decisions (mostly outside the frame), holes without partners, and the zones."""
	excluded = [(h, s) for h, s, ok in zip(hole_map.holes, cells.in_frame, cells.reliable, strict=True) if not ok]
	print(
		f"  holes used for decisions: {len(hole_map.holes) - len(excluded)} of {len(hole_map.holes)} "
		f"(left out when under {MIN_IN_FRAME:.0%} of the cell is inside the frame)"
	)
	for hole, share in excluded:
		print(f"    left out: {hole.hole_id}  {share:.0%} in frame")
	lonely = [h.hole_id for i, h in enumerate(hole_map.holes) if not cells.pairs_of(i)]
	print(
		f"  channels are {hole_map.channel_axis}s; holes with no partner in either direction "
		f"(crowding can't be measured there): {', '.join(lonely) or 'none'}"
	)
	no_across = [h.hole_id for h, cross in zip(hole_map.holes, cells.cross_neighbours, strict=True) if not cross]
	no_along = [h.hole_id for h, along in zip(hole_map.holes, cells.along_neighbours, strict=True) if not along]
	print(f"    no partner in the next channel: {', '.join(no_across) or 'none'}")
	print(f"    no partner along its channel: {', '.join(no_along) or 'none'}")
	for zone in hole_map.zones:
		print(f"  zone {zone.name}: {int(zone_mask(zone, hole_map.image_size).sum())} px, {len(zone.polygon)} corners")


def write_overlay_sheet(index_csv: Path, frames_root: Path, out_dir: Path, hole_map: HoleMap, cells: Cells) -> None:
	"""The cells drawn on the first, middle and last usable frames of the map's own period, stacked."""
	files = [row.file for row in map_frames(index_csv, hole_map)[0]]  # the map's own period
	if not files:
		raise SystemExit("No usable frames in this period; check data/frame_index.csv and the map's dates")
	picks = [files[0], files[len(files) // 2], files[-1]]
	panels = []
	for name in picks:
		image = read_image(frames_root / hole_map.camera_id / name)
		panel = draw_overlay(image, hole_map, cells)
		put_outlined_text(panel, name, (8, panel.shape[0] - 10), 0.5)
		panels.append(panel)
	out_dir.mkdir(parents=True, exist_ok=True)
	out = out_dir / f"{hole_map.camera_id}_{hole_map.period}.jpg"
	cv2.imwrite(str(out), np.vstack(panels))
	print(f"  overlays on {len(picks)} of {len(files)} usable frames: {out}")


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--hole-map", type=Path, required=True)
	parser.add_argument("--frames-root", type=Path, required=True)
	parser.add_argument("--index-csv", type=Path, default=Path("data/frame_index.csv"))
	parser.add_argument("--out-dir", type=Path, default=Path("data/checks/hole_maps"))
	args = parser.parse_args()

	hole_map = HoleMap.load(args.hole_map)
	cells = build_cells(hole_map)
	print_summary(args.hole_map.name, hole_map, cells, map_checks(hole_map, cells))
	print_left_out(hole_map, cells)
	write_overlay_sheet(args.index_csv, args.frames_root, args.out_dir, hole_map, cells)


if __name__ == "__main__":
	main()
