"""Label MobileSAM outlines as plant / not plant, to train the plant filter.

Usage (from the cv/ folder):
	uv run python tools/label_masks.py --frames-root E:\\Claude

Shows one outline at a time: on the left the outlined area is lit and the rest dimmed, on the
right the same crop untouched (to judge leaf texture), and below, the whole frame with the
crop marked. Decide only by what is INSIDE the cyan outline:

	y  plant      almost all of it (about 90%+) is leaf or stem, any colour, any size,
		including a single leaf or a whole closed canopy
	n  not plant  mostly board, hole, pot, wall, floor, cable, shadow or glare
	m  mixed      big parts of both (e.g. a plant plus a slab of board)
	s  skip       can't tell
	b  back       undo the last answer and show it again
	q  quit       answers are saved after every key, so you can stop and resume any time

About 400 answers is enough (roughly 45 minutes). The order is shuffled, so stopping early
still covers every camera. Answers go to labels/plant_masks/labels.csv.
"""

import argparse
import csv
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

from leafy_cv.plant_filter import unpack_masks

WINDOW = "label masks"
LABELS = {ord("y"): "plant", ord("n"): "not_plant", ord("m"): "mixed", ord("s"): "skip"}
PANEL_HEIGHT = 360
MAX_PANEL_WIDTH = 480
THUMB_WIDTH = 352
TARGET_LABELS = 400
OUTLINE = (255, 255, 0)  # cyan in BGR


def crop_box(bbox: tuple[int, int, int, int], width: int, height: int) -> tuple[int, int, int, int]:
	"""The outline's box plus 30% context on each side, at least 120 px across."""
	x0, y0, x1, y1 = bbox
	pad_x = max(int(0.3 * (x1 - x0)), (120 - (x1 - x0)) // 2, 10)
	pad_y = max(int(0.3 * (y1 - y0)), (120 - (y1 - y0)) // 2, 10)
	return max(0, x0 - pad_x), max(0, y0 - pad_y), min(width, x1 + pad_x + 1), min(height, y1 + pad_y + 1)


def fit(image: np.ndarray) -> np.ndarray:
	scale = min(PANEL_HEIGHT / image.shape[0], MAX_PANEL_WIDTH / image.shape[1])
	size = (max(1, int(image.shape[1] * scale)), max(1, int(image.shape[0] * scale)))
	return cv2.resize(image, size, interpolation=cv2.INTER_NEAREST if scale > 1 else cv2.INTER_AREA)


def render(image: np.ndarray, mask: np.ndarray, row: dict, status: str) -> np.ndarray:
	height, width = image.shape[:2]
	x0, y0, x1, y1 = crop_box(tuple(int(v) for v in row["bbox"].split()), width, height)
	lit = image.copy()
	lit[~mask] = (lit[~mask] * 0.35).astype(np.uint8)
	contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
	cv2.drawContours(lit, contours, -1, OUTLINE, 1)
	left, right = fit(lit[y0:y1, x0:x1]), fit(image[y0:y1, x0:x1])

	thumb = image.copy()
	cv2.drawContours(thumb, contours, -1, OUTLINE, 2)
	cv2.rectangle(thumb, (x0, y0), (x1, y1), (255, 255, 255), 2)
	thumb = cv2.resize(thumb, (THUMB_WIDTH, int(height * THUMB_WIDTH / width)))

	gap = 8
	top_width = left.shape[1] + gap + right.shape[1]
	canvas_width = max(top_width, THUMB_WIDTH + 440)
	canvas = np.full((PANEL_HEIGHT + gap + thumb.shape[0] + 8, canvas_width, 3), 32, np.uint8)
	canvas[: left.shape[0], : left.shape[1]] = left
	canvas[: right.shape[0], left.shape[1] + gap : left.shape[1] + gap + right.shape[1]] = right
	ty = PANEL_HEIGHT + gap
	canvas[ty : ty + thumb.shape[0], :THUMB_WIDTH] = thumb
	lines = [
		*status.split("\n"),
		"",
		f"{row['camera_id']}  {row['captured_at'][:16].replace('T', ' ')}",
		f"prompt: {row['prompt']} {row['hole_id']}".rstrip(),
		"",
		"y plant   n not plant   m mixed",
		"s skip    b back        q quit",
		"Judge only what is inside the cyan outline.",
	]
	for i, line in enumerate(lines):
		cv2.putText(
			canvas, line, (THUMB_WIDTH + 14, ty + 22 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (235, 235, 235), 1
		)
	return canvas


def read_labels(path: Path) -> list[dict]:
	if not path.exists():
		return []
	with open(path, encoding="utf-8") as handle:
		return list(csv.DictReader(handle))


def write_labels(path: Path, labels: list[dict]) -> None:
	tmp = path.with_suffix(".tmp")
	with open(tmp, "w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=["candidate_id", "label", "labelled_at"])
		writer.writeheader()
		writer.writerows(labels)
	tmp.replace(path)  # never leaves a half-written file behind


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--frames-root", type=Path, required=True)
	parser.add_argument("--dir", type=Path, default=Path("labels/plant_masks"))
	args = parser.parse_args()

	with open(args.dir / "candidates.csv", encoding="utf-8") as handle:
		candidates = sorted(csv.DictReader(handle), key=lambda r: int(r["order"]))
	masks = np.load(args.dir / "masks.npz")
	labels_path = args.dir / "labels.csv"
	labels = read_labels(labels_path)
	done = {row["candidate_id"] for row in labels}
	queue = [row for row in candidates if row["candidate_id"] not in done]
	print(__doc__)
	print(f"{len(labels)} answered so far, {len(queue)} to go.")
	if not queue:
		return

	cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
	frame_cache: dict[str, np.ndarray] = {}
	position = 0
	while position < len(queue):
		row = queue[position]
		path = args.frames_root / row["camera_id"] / row["file"]
		if str(path) not in frame_cache:
			image = cv2.imread(str(path))
			if image is None:
				raise SystemExit(f"Could not read {path}; check --frames-root")
			frame_cache = {str(path): image}  # keep one frame in memory
		image = frame_cache[str(path)]
		mask = unpack_masks(masks[row["candidate_id"]], int(row["width"]))[int(row["best"])]
		counts = {name: sum(r["label"] == name for r in labels) for name in LABELS.values()}
		answered = len(labels)
		status = (
			f"{answered} answered (aim: {TARGET_LABELS})\n"
			f"plant {counts['plant']}  not {counts['not_plant']}  mixed {counts['mixed']}  skip {counts['skip']}"
		)
		cv2.imshow(WINDOW, render(image, mask, row, status))
		key = cv2.waitKey(0) & 0xFF
		if key in LABELS:
			labels.append(
				{
					"candidate_id": row["candidate_id"],
					"label": LABELS[key],
					"labelled_at": datetime.now().isoformat(timespec="seconds"),
				}
			)
			write_labels(labels_path, labels)
			position += 1
		elif key == ord("b") and labels:
			undone = labels.pop()
			write_labels(labels_path, labels)
			if position > 0 and queue[position - 1]["candidate_id"] == undone["candidate_id"]:
				position -= 1
			else:  # answered in an earlier session: put it back in front
				queue.insert(position, next(r for r in candidates if r["candidate_id"] == undone["candidate_id"]))
		elif key in (ord("q"), 27):
			break
		if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
			break
	cv2.destroyAllWindows()
	print(f"Saved {len(labels)} answers to {labels_path}.")
	if len(labels) >= TARGET_LABELS:
		print("Enough to train: uv run python tools/train_plant_filter.py --frames-root <frames folder>")


if __name__ == "__main__":
	main()
