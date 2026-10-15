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
from pathlib import Path

import cv2
import numpy as np

from leafy_cv.drawing import dim_outside
from leafy_cv.labelling import THUMB_WIDTH, LabelSession, PlantLabel, compose, read_labels, run_session, thumbnail
from leafy_cv.plant_filter import unpack_masks

WINDOW = "label masks"
LABELS = {
	ord("y"): PlantLabel.PLANT,
	ord("n"): PlantLabel.NOT_PLANT,
	ord("m"): PlantLabel.MIXED,
	ord("s"): PlantLabel.SKIP,
}
PANEL_HEIGHT = 360
MAX_PANEL_WIDTH = 480
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
	lit = dim_outside(image, mask)
	contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
	cv2.drawContours(lit, contours, -1, OUTLINE, 1)
	left, right = fit(lit[y0:y1, x0:x1]), fit(image[y0:y1, x0:x1])
	outlined = image.copy()
	cv2.drawContours(outlined, contours, -1, OUTLINE, 2)
	thumb = thumbnail(outlined, (x0, y0, x1, y1))
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
	width_needed = max(left.shape[1] + 8 + right.shape[1], THUMB_WIDTH + 440)
	return compose(left, right, thumb, lines, PANEL_HEIGHT, width_needed)


class CandidateScreens:
	"""Draws the screen for one outline; keeps one frame in memory (the last one read)."""

	def __init__(self, frames_root: Path, masks, session: LabelSession):
		self.frames_root, self.masks, self.session = frames_root, masks, session
		self.frame_path, self.frame = None, None

	def __call__(self, row: dict) -> np.ndarray:
		path = self.frames_root / row["camera_id"] / row["file"]
		if path != self.frame_path:
			image = cv2.imread(str(path))
			if image is None:
				raise SystemExit(f"Could not read {path}; check --frames-root")
			self.frame_path, self.frame = path, image
		mask = unpack_masks(self.masks[row["candidate_id"]], int(row["width"]))[int(row["best"])]
		return render(self.frame, mask, row, self.status())

	def status(self) -> str:
		s = self.session
		return (
			f"{len(s.labels)} answered (aim: {TARGET_LABELS})\n"
			f"plant {s.count(PlantLabel.PLANT)}  not {s.count(PlantLabel.NOT_PLANT)}  "
			f"mixed {s.count(PlantLabel.MIXED)}  skip {s.count(PlantLabel.SKIP)}"
		)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--frames-root", type=Path, required=True)
	parser.add_argument("--dir", type=Path, default=Path("labels/plant_masks"))
	args = parser.parse_args()

	with open(args.dir / "candidates.csv", encoding="utf-8") as handle:
		candidates = sorted(csv.DictReader(handle), key=lambda r: int(r["order"]))
	labels_path = args.dir / "labels.csv"
	with np.load(args.dir / "masks.npz") as masks:
		session = LabelSession(candidates, "candidate_id", read_labels(labels_path))
		print(__doc__)
		print(f"{len(session.labels)} answered so far, {len(session.queue)} to go.")
		if not session.queue:
			return
		run_session(session, labels_path, LABELS, CandidateScreens(args.frames_root, masks, session), WINDOW)
	print(f"Saved {len(session.labels)} answers to {labels_path}.")
	if len(session.labels) >= TARGET_LABELS:
		print("Enough to train: uv run python tools/train_plant_filter.py --frames-root <frames folder>")


if __name__ == "__main__":
	main()
