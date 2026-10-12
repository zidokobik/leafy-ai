"""Index every archived frame: which period it belongs to, and whether it's safe to analyse.

Usage (from the cv/ folder):
	uv run python tools/build_frame_index.py --frames-root E:\\Claude

Writes:
	data/frame_index.csv   one row per frame
	data/periods.csv       one row per camera period: the hole-map versions you need
	data/checks/events/    a before | after image for every frame that isn't plain "ok"

Uses config/fixed_parts.json (where each camera's fixed parts are) and
trained/plant_filter.json (to see where the plants are). About 1 s per frame.

Refuses to replace an existing frame_index.csv / periods.csv unless --overwrite is given: the current ones were
corrected by hand on 11 Oct (the tool can't recreate those corrections). Back them up first.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

from leafy_cv.drift import DEFAULT_FIXED_PARTS, Alignment, align, extract_features, load_fixed_parts
from leafy_cv.frame_index import OK, USABLE_STATUSES, label_sequence
from leafy_cv.frames import Frame, list_frames, read_image
from leafy_cv.plant_filter import PlantFilter
from leafy_cv.scene import plant_change, plant_cover, plant_tiles

DEFAULT_PLANT_FILTER = Path(__file__).resolve().parents[1] / "trained" / "plant_filter.json"


def save_event_image(before: Frame, after: Frame, status: str, detail: str, out_dir: Path) -> None:
	images = []
	for frame, title in ((before, "compared with"), (after, status)):
		image = read_image(frame.path)
		text = f"{title}: {frame.captured_at:%d %b %H:%M}"
		cv2.putText(image, text, (10, image.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
		cv2.putText(image, text, (10, image.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
		images.append(image)
	pair = np.hstack(images)
	cv2.putText(pair, detail, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 4)
	cv2.putText(pair, detail, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
	name = f"{after.camera_id}_{after.captured_at:%Y%m%d_%H%M}_{status}.jpg"
	cv2.imwrite(str(out_dir / name), pair)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--frames-root", type=Path, required=True, help="folder holding one sub-folder per camera")
	parser.add_argument("--out-dir", type=Path, default=Path("data"))
	parser.add_argument("--fixed-parts", type=Path, default=DEFAULT_FIXED_PARTS)
	parser.add_argument("--plant-filter", type=Path, default=DEFAULT_PLANT_FILTER)
	parser.add_argument("--no-event-images", action="store_true")
	parser.add_argument(
		"--overwrite",
		action="store_true",
		help="replace an existing frame_index.csv / periods.csv (back them up first)",
	)
	args = parser.parse_args()
	existing = [args.out_dir / name for name in ("frame_index.csv", "periods.csv") if (args.out_dir / name).exists()]
	if existing and not args.overwrite:
		raise SystemExit(
			f"{', '.join(str(p) for p in existing)} already exist (the current ones were corrected by hand on 11 Oct). "
			"Back them up and pass --overwrite to rebuild, or use another --out-dir."
		)

	fixed_parts = load_fixed_parts(args.fixed_parts)
	plant_filter = PlantFilter.load(args.plant_filter)

	by_camera, skipped = list_frames(args.frames_root)
	if not by_camera:
		raise SystemExit(f"No frames found under {args.frames_root}\\<camera_id>\\<camera_id>_YYYYMMDD_HHMMSS.jpg")
	events_dir = args.out_dir / "checks" / "events"
	events_dir.mkdir(parents=True, exist_ok=True)

	index_rows, period_rows = [], []
	for camera_id, frames in sorted(by_camera.items()):
		regions = fixed_parts.get(camera_id)
		if regions is None:
			print(f"  WARNING: {camera_id} has no fixed parts in {args.fixed_parts}; matching on the whole frame")
		print(f"{camera_id}: {len(frames)} frames, finding fixed-part corners and plants ...", flush=True)
		features, tiles = [], []
		for frame in frames:
			image = read_image(frame.path)
			features.append(extract_features(image, regions))
			tiles.append(plant_tiles(image, plant_filter))
		first_of_day = [
			i == 0 or frames[i - 1].captured_at.date() != f.captured_at.date() for i, f in enumerate(frames)
		]

		def compare(i: int, j: int) -> Alignment:
			alignment = align(features[i], features[j])
			return Alignment(**{**alignment.__dict__, "plant_change": plant_change(tiles[i], tiles[j])})

		labels = label_sequence(len(frames), compare, can_anchor=[not first for first in first_of_day])

		for k, (frame, label) in enumerate(zip(frames, labels, strict=True)):
			index_rows.append(
				{
					"camera_id": camera_id,
					"captured_at": frame.captured_at.isoformat(),
					"file": frame.path.name,
					"period": f"P{label.period}",
					"status": label.status,
					"usable": label.status in USABLE_STATUSES,
					"first_of_day": first_of_day[k],
					"plant_cover": f"{plant_cover(tiles[k]):.3f}",
					"compared_with": frames[label.compared_with].path.name if label.compared_with is not None else "",
					"inliers": label.inliers if label.inliers is not None else "",
					"shift_px": f"{label.shift_px:.1f}" if label.shift_px is not None else "",
					"rotation_deg": f"{label.rotation_deg:.2f}" if label.rotation_deg is not None else "",
					"plant_change": f"{label.plant_change:.3f}" if label.plant_change is not None else "",
				}
			)
			if label.status != OK and label.compared_with is not None and not args.no_event_images:
				detail = (
					f"inliers {label.inliers}, shift {label.shift_px or 0:.1f} px, "
					f"plant change {label.plant_change or 0:.0%}"
				)
				save_event_image(frames[label.compared_with], frame, label.status, detail, events_dir)

		for period in sorted({label.period for label in labels}):
			members = [(f, lab) for f, lab in zip(frames, labels, strict=True) if lab.period == period]
			period_rows.append(
				{
					"camera_id": camera_id,
					"period": f"P{period}",
					"start": members[0][0].captured_at.isoformat(),
					"end": members[-1][0].captured_at.isoformat(),
					"frames": len(members),
					"usable_frames": sum(lab.status in USABLE_STATUSES for _, lab in members),
					"started_by": members[0][1].status if period > 1 else "first frame",
					"note": "",
				}
			)

	args.out_dir.mkdir(parents=True, exist_ok=True)
	for name, rows in (("frame_index.csv", index_rows), ("periods.csv", period_rows)):
		with open(args.out_dir / name, "w", newline="", encoding="utf-8") as handle:
			writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
			writer.writeheader()
			writer.writerows(rows)

	print(f"\nIndexed {len(index_rows)} frames from {len(by_camera)} cameras; skipped {len(skipped)} other .jpg files.")
	print("\nStatus counts per camera:")
	for camera_id in sorted(by_camera):
		counts = Counter(row["status"] for row in index_rows if row["camera_id"] == camera_id)
		print(f"  {camera_id}: " + ", ".join(f"{status} {n}" for status, n in counts.most_common()))
	print("\nPeriods (each needs its own hole map):")
	for row in period_rows:
		print(
			f"  {row['camera_id']} {row['period']}: {row['start'][:16]} -> {row['end'][:16]}"
			f"  {row['usable_frames']}/{row['frames']} usable  (started by {row['started_by']})"
		)
	print(f"\nWrote {args.out_dir / 'frame_index.csv'}, {args.out_dir / 'periods.csv'}")
	print(f"Check images: {events_dir}")


if __name__ == "__main__":
	main()
