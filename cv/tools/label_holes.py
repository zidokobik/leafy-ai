"""Label hole crops: do this plant's leaves touch the leaves of ANY neighbouring plant, in the same channel
or in the next channel? (12 Oct: both directions; the 7 Oct question asked about the next channel only.)

Usage (from the cv/ folder, after tools/make_hole_items.py):
	uv run python tools/label_holes.py --frames-root E:\\Claude

Shows one plant at a time. Left: a close-up with the plant marked by a yellow dot and its partners by
white dots: its neighbours along its own channel and the plant(s) it faces in the next channel. Right: the
same close-up untouched (dots are small; look here for leaves). Below: the whole frame with the close-up
marked. Judge only yellow vs white; one touching white-dot plant is enough:

	y  crowded    the yellow plant's leaves meet or overlap the leaves of any white-dot plant
	n  not yet    there is still visible board between the yellow plant and every white-dot plant
	e  empty      there is no plant at the yellow dot (or only a seedling too small to judge)
	u  unsure     can't tell (blur, glare, a person in the way, or the gap is hidden, e.g. by a plant in front)
	b  back       undo the last answer and show it again
	q  quit       answers are saved after every key, so you can stop and resume any time

No numbers are shown on purpose: the labels check the numbers. About 20 minutes per 100.
Answers go to labels/readiness/labels.csv.
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from leafy_cv.hole_map import HoleMap, build_cells

WINDOW = "label holes"
LABELS = {ord("y"): "crowded", ord("n"): "not_crowded", ord("e"): "empty", ord("u"): "unsure"}
PANEL = 340
THUMB_WIDTH = 352
DOT_RADIUS = 4  # px in the close-up


def render(image: np.ndarray, hole_map: HoleMap, cells, hole_index: int, status: str) -> np.ndarray:
	height, width = image.shape[:2]
	hole = hole_map.holes[hole_index]
	region = cells.cell(hole_index) | cells.corridors[hole_index]
	partners = [hole_map.holes[j] for j in cells.partners(hole_index)]  # both directions (12 Oct)
	for j in cells.partners(hole_index):
		region |= cells.cell(j)
	ys, xs = np.nonzero(region)
	pad = int(0.4 * cells.spacing[hole_index])
	x0, y0 = max(0, xs.min() - pad), max(0, ys.min() - pad)
	x1, y1 = min(width, xs.max() + pad + 1), min(height, ys.max() + pad + 1)

	scale = PANEL / max(x1 - x0, y1 - y0)
	size = (int((x1 - x0) * scale), int((y1 - y0) * scale))
	left = cv2.resize(image[y0:y1, x0:x1], size, interpolation=cv2.INTER_LINEAR)
	right = left.copy()
	# dots drawn after resizing, so they stay the same size however wide the close-up is (12 Oct: with partners
	# in both directions the close-ups got wider and the old 2 px dots shrank to specks)
	for point, colour in [(p, (255, 255, 255)) for p in partners] + [(hole, (0, 255, 255))]:
		at = (round((point.x - x0) * scale), round((point.y - y0) * scale))
		cv2.circle(left, at, DOT_RADIUS + 1, (0, 0, 0), -1)
		cv2.circle(left, at, DOT_RADIUS, colour, -1)

	thumb = image.copy()
	cv2.rectangle(thumb, (x0, y0), (x1, y1), (255, 255, 255), 2)
	thumb = cv2.resize(thumb, (THUMB_WIDTH, int(height * THUMB_WIDTH / width)))

	gap = 8
	canvas = np.full((PANEL + gap + thumb.shape[0] + 8, max(2 * PANEL + gap, THUMB_WIDTH + 470), 3), 32, np.uint8)
	canvas[: left.shape[0], : left.shape[1]] = left
	canvas[: right.shape[0], left.shape[1] + gap : left.shape[1] + gap + right.shape[1]] = right
	ty = PANEL + gap
	canvas[ty : ty + thumb.shape[0], :THUMB_WIDTH] = thumb
	lines = [
		*status.split("\n"),
		"",
		"Do the leaves of the YELLOW-dot plant touch",
		"the leaves of ANY WHITE-dot plant",
		"(same channel or next channel)?",
		"",
		"y crowded   n not yet   e empty   u unsure",
		"b back      q quit",
	]
	for i, line in enumerate(lines):
		at = (THUMB_WIDTH + 14, ty + 22 + 22 * i)
		cv2.putText(canvas, line, at, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (235, 235, 235), 1)
	return canvas


def read_labels(path: Path) -> list[dict]:
	if not path.exists():
		return []
	with open(path, encoding="utf-8") as handle:
		return list(csv.DictReader(handle))


def write_labels(path: Path, labels: list[dict]) -> None:
	tmp = path.with_suffix(".tmp")
	with open(tmp, "w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=["item_id", "label", "labelled_at"])
		writer.writeheader()
		writer.writerows(labels)
	tmp.replace(path)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--frames-root", type=Path, required=True)
	parser.add_argument("--dir", type=Path, default=Path("labels/readiness"))
	parser.add_argument("--hole-maps", type=Path, default=Path("hole_maps"))
	args = parser.parse_args()

	with open(args.dir / "items.csv", encoding="utf-8") as handle:
		items = sorted(csv.DictReader(handle), key=lambda r: int(r["order"]))
	hole_maps = {}
	for path in sorted(args.hole_maps.glob("*.json")):
		hole_map = HoleMap.load(path)
		hole_maps[(hole_map.camera_id, hole_map.period)] = hole_map
	cells_cache: dict[tuple[str, str], object] = {}
	labels_path = args.dir / "labels.csv"
	labels = read_labels(labels_path)
	done = {row["item_id"] for row in labels}
	queue = [item for item in items if item["item_id"] not in done]
	print(__doc__)
	print(f"{len(labels)} answered so far, {len(queue)} to go.")
	if not queue:
		return

	cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
	position = 0
	while position < len(queue):
		item = queue[position]
		key_map = (item["camera_id"], item["period"])
		if key_map not in hole_maps:
			raise SystemExit(f"No hole map for {item['camera_id']} {item['period']} in {args.hole_maps}")
		hole_map = hole_maps[key_map]
		if key_map not in cells_cache:
			cells_cache[key_map] = build_cells(hole_map)
		cells = cells_cache[key_map]
		index = next((i for i, h in enumerate(hole_map.holes) if h.hole_id == item["hole_id"]), None)
		if index is None:
			raise SystemExit(f"{item['hole_id']} is not in the {item['camera_id']} {item['period']} map (map changed?)")
		path = args.frames_root / item["camera_id"] / item["file"]
		image = cv2.imread(str(path))
		if image is None:
			raise SystemExit(f"Could not read {path}; check --frames-root")
		counts = {name: sum(r["label"] == name for r in labels) for name in LABELS.values()}
		status = (
			f"{len(labels)} of {len(items)} answered\n"
			f"crowded {counts['crowded']}  not yet {counts['not_crowded']}  "
			f"empty {counts['empty']}  unsure {counts['unsure']}"
		)
		cv2.imshow(WINDOW, render(image, hole_map, cells, index, status))
		key = cv2.waitKey(0) & 0xFF
		if key in LABELS:
			labels.append(
				{
					"item_id": item["item_id"],
					"label": LABELS[key],
					"labelled_at": datetime.now().astimezone().isoformat(timespec="seconds"),
				}
			)
			write_labels(labels_path, labels)
			position += 1
		elif key == ord("b") and labels:
			undone = labels.pop()
			write_labels(labels_path, labels)
			if position > 0 and queue[position - 1]["item_id"] == undone["item_id"]:
				position -= 1
			else:  # answered in an earlier session: put it back in front
				queue.insert(position, next(i for i in items if i["item_id"] == undone["item_id"]))
		elif key in (ord("q"), 27):
			break
		if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
			break
	cv2.destroyAllWindows()
	print(f"Saved {len(labels)} answers to {labels_path}.")
	print("Then: uv run python tools/evaluate_readiness.py")


if __name__ == "__main__":
	main()
