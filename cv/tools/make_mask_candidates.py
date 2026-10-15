"""Make the outlines (MobileSAM masks) to label as plant / not plant.

Usage (from the cv/ folder, after tools/download_weights.py):
	uv run python tools/make_mask_candidates.py --frames-root E:\\Claude

Picks a spread of midday frames from every camera (all dates, all lighting), then runs MobileSAM:
- frames covered by a hole map: one prompt per hole centre, with the touching holes as "not this" points. The
  pipeline also marks the holes each hole faces in the next channel, so its outlines are close to these, not
  identical (a known limitation; retraining would fix it).
- other frames: prompts at random points, which gives a varied mix of plant, board,
  pots, walls and glare.

Writes labels/plant_masks/candidates.csv (one row per outline, in a shuffled order so labelling
can stop at any point and still cover every camera) and masks.npz. Then label them with
tools/label_masks.py. Takes about 10-20 s per frame on a laptop CPU.
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path

import numpy as np

from leafy_cv.csv_files import write_csv
from leafy_cv.frames import TIMESTAMP_STRIP_PX, WATERMARK_PX, read_image
from leafy_cv.hole_map import HoleMap, build_cells
from leafy_cv.plant_filter import MIN_MASK_PIXELS, pack_masks
from leafy_cv.segment import PointMasks, Segmenter

EXCLUDED_HOUR = 5  # camera 1's 05:00 frames are shifted, and 05:00 light differs
TARGET_HOUR = 12
EDGE_MARGIN_PX = 12
# Always include: camera 2's last frame before the 30 Sep transfer, the most closed canopy we
# have, with the palest leaves (where a simple green-pixel test failed).
ALSO = ("level1_camera2_20260930_100027.jpg",)


def pick_frames(index_csv: Path, frames_per_camera: int, also: tuple[str, ...] = ()) -> list[dict]:
	"""For each camera, the usable frame nearest midday on `frames_per_camera` evenly spread dates,
	plus the frames named in `also`."""
	by_camera: dict[str, list[dict]] = {}
	extra = []
	with open(index_csv, encoding="utf-8") as handle:
		for row in csv.DictReader(handle):
			when = datetime.fromisoformat(row["captured_at"])
			if row["file"] in also:
				extra.append({**row, "when": when})
			elif row["usable"] == "True" and when.hour != EXCLUDED_HOUR:
				by_camera.setdefault(row["camera_id"], []).append({**row, "when": when})
	picks = []
	for rows in by_camera.values():
		dates = sorted({r["when"].date() for r in rows})
		chosen = sorted({round(i) for i in np.linspace(0, len(dates) - 1, min(frames_per_camera, len(dates)))})
		for i in chosen:
			day = [r for r in rows if r["when"].date() == dates[i]]
			picks.append(min(day, key=lambda r: abs(r["when"].hour + r["when"].minute / 60 - TARGET_HOUR)))
	missing = set(also) - {r["file"] for r in extra}
	if missing:
		raise SystemExit(f"Not in {index_csv}: {', '.join(sorted(missing))}")
	return sorted(picks + extra, key=lambda r: (r["camera_id"], r["when"]))


def find_hole_map(hole_maps: list[HoleMap], camera_id: str, when: datetime) -> HoleMap | None:
	for hole_map in hole_maps:
		start = datetime.fromisoformat(hole_map.valid_from)
		end = datetime.fromisoformat(hole_map.valid_to) if hole_map.valid_to else None
		if hole_map.camera_id == camera_id and start <= when and (end is None or when <= end):
			return hole_map
	return None


def random_points(rng: np.random.Generator, count: int, width: int, height: int) -> np.ndarray:
	points = []
	while len(points) < count:
		x = rng.uniform(EDGE_MARGIN_PX, width - EDGE_MARGIN_PX)
		y = rng.uniform(TIMESTAMP_STRIP_PX, height - EDGE_MARGIN_PX)
		if x > width - WATERMARK_PX[0] and y > height - WATERMARK_PX[1]:
			continue
		points.append((x, y))
	return np.array(points, np.float32)


def prompts(
	hole_map: HoleMap | None, rng: np.random.Generator, count: int, shape: tuple[int, int]
) -> tuple[np.ndarray, list[list[int]] | None, list[str] | None]:
	"""Prompt points, their "not this" points and hole ids: the hole centres with their touching holes when a map
	covers the frame (see the module docstring), else random points."""
	if hole_map is None:
		height, width = shape
		return random_points(rng, count, width, height), None, None
	negatives = [sorted(nb) for nb in build_cells(hole_map).neighbours]
	return hole_map.centres(), negatives, [h.hole_id for h in hole_map.holes]


def candidates(
	pick: dict, results: list[PointMasks], hole_map: HoleMap | None, hole_ids: list[str] | None, width: int
) -> tuple[list[dict], dict[str, np.ndarray]]:
	"""candidates.csv rows and packed masks for one frame's outlines (MobileSAM's top-rated one at least
	MIN_MASK_PIXELS)."""
	stamp = pick["when"].strftime("%Y%m%d_%H%M")
	rows, packed = [], {}
	for k, result in enumerate(results):
		best = result.best
		chosen = result.masks[best]
		if chosen.sum() < MIN_MASK_PIXELS:
			continue
		ys, xs = np.nonzero(chosen)
		candidate_id = f"{pick['camera_id']}_{stamp}_{k:03d}"
		packed[candidate_id] = pack_masks(result.masks)
		rows.append(
			{
				"candidate_id": candidate_id,
				"camera_id": pick["camera_id"],
				"file": pick["file"],
				"captured_at": pick["captured_at"],
				"prompt": "hole" if hole_map is not None else "random",
				"hole_id": hole_ids[k] if hole_ids else "",
				"x": f"{result.point[0]:.1f}",
				"y": f"{result.point[1]:.1f}",
				"best": best,
				**{f"score_{c}": f"{result.scores[c]:.3f}" for c in range(3)},
				**{f"area_{c}": int(result.masks[c].sum()) for c in range(3)},
				"bbox": f"{xs.min()} {ys.min()} {xs.max()} {ys.max()}",
				"width": width,
			}
		)
	return rows, packed


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--frames-root", type=Path, required=True)
	parser.add_argument("--index-csv", type=Path, default=Path("data/frame_index.csv"))
	parser.add_argument("--hole-maps", type=Path, default=Path("hole_maps"))
	parser.add_argument("--out-dir", type=Path, default=Path("labels/plant_masks"))
	parser.add_argument("--frames-per-camera", type=int, default=7)
	parser.add_argument("--points-per-frame", type=int, default=20, help="random prompts on frames without a map")
	parser.add_argument("--also", nargs="*", default=list(ALSO), help="extra frame file names to include")
	parser.add_argument("--seed", type=int, default=0)
	parser.add_argument("--threads", type=int, default=None)
	args = parser.parse_args()

	if (args.out_dir / "labels.csv").exists():
		raise SystemExit(
			f"{args.out_dir} already has labels; new candidates would not match them. Use another --out-dir."
		)
	rng = np.random.default_rng(args.seed)
	hole_maps = [HoleMap.load(p) for p in sorted(args.hole_maps.glob("*.json"))]
	picks = pick_frames(args.index_csv, args.frames_per_camera, tuple(args.also))
	print(f"{len(picks)} frames from {len({p['camera_id'] for p in picks})} cameras; loading MobileSAM ...", flush=True)
	segmenter = Segmenter(threads=args.threads)

	rows, packed = [], {}
	for n, pick in enumerate(picks, start=1):
		image = read_image(args.frames_root / pick["camera_id"] / pick["file"])
		hole_map = find_hole_map(hole_maps, pick["camera_id"], pick["when"])
		points, negatives, hole_ids = prompts(hole_map, rng, args.points_per_frame, image.shape[:2])
		segmenter.set_image(image)
		frame_rows, frame_masks = candidates(
			pick, segmenter.predict(points, negatives), hole_map, hole_ids, image.shape[1]
		)
		rows += frame_rows
		packed |= frame_masks
		source = f"hole map {hole_map.camera_id} {hole_map.period}" if hole_map else "random points"
		print(f"  [{n}/{len(picks)}] {pick['file']}: {len(frame_rows)} outlines ({source})", flush=True)

	rows = [rows[i] | {"order": rank} for rank, i in enumerate(rng.permutation(len(rows)))]
	args.out_dir.mkdir(parents=True, exist_ok=True)
	write_csv(args.out_dir / "candidates.csv", list(rows[0]), rows)
	np.savez_compressed(args.out_dir / "masks.npz", **packed)
	print(f"\nWrote {len(rows)} outlines to {args.out_dir}. Next: tools/label_masks.py")


if __name__ == "__main__":
	main()
