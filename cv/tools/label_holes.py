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
from pathlib import Path

import cv2
import numpy as np

from leafy_cv.hole_map import Cells, HoleMap, build_cells
from leafy_cv.labelling import THUMB_WIDTH, LabelSession, ReadinessLabel, compose, read_labels, run_session, thumbnail

WINDOW = "label holes"
LABELS = {
	ord("y"): ReadinessLabel.CROWDED,
	ord("n"): ReadinessLabel.NOT_CROWDED,
	ord("e"): ReadinessLabel.EMPTY,
	ord("u"): ReadinessLabel.UNSURE,
}
PANEL = 340
DOT_RADIUS = 4  # px in the close-up
INSTRUCTIONS = [
	"",
	"Do the leaves of the YELLOW-dot plant touch",
	"the leaves of ANY WHITE-dot plant",
	"(same channel or next channel)?",
	"",
	"y crowded   n not yet   e empty   u unsure",
	"b back      q quit",
]


def render(image: np.ndarray, hole_map: HoleMap, cells: Cells, hole_index: int, status: str) -> np.ndarray:
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

	thumb = thumbnail(image.copy(), (x0, y0, x1, y1))
	lines = [*status.split("\n"), *INSTRUCTIONS]
	return compose(left, right, thumb, lines, PANEL, max(2 * PANEL + 8, THUMB_WIDTH + 470))


class ItemScreens:
	"""Draws the screen for one labelling item; loads each hole map's cells once."""

	def __init__(self, frames_root: Path, maps_dir: Path, session: LabelSession):
		self.frames_root, self.maps_dir, self.session = frames_root, maps_dir, session
		self.hole_maps: dict[tuple[str, str], HoleMap] = {}
		for path in sorted(maps_dir.glob("*.json")):
			hole_map = HoleMap.load(path)
			self.hole_maps[(hole_map.camera_id, hole_map.period)] = hole_map
		self.cells: dict[tuple[str, str], Cells] = {}

	def __call__(self, item: dict) -> np.ndarray:
		key = (item["camera_id"], item["period"])
		if key not in self.hole_maps:
			raise SystemExit(f"No hole map for {item['camera_id']} {item['period']} in {self.maps_dir}")
		hole_map = self.hole_maps[key]
		if key not in self.cells:
			self.cells[key] = build_cells(hole_map)
		index = next((i for i, h in enumerate(hole_map.holes) if h.hole_id == item["hole_id"]), None)
		if index is None:
			raise SystemExit(f"{item['hole_id']} is not in the {item['camera_id']} {item['period']} map (map changed?)")
		path = self.frames_root / item["camera_id"] / item["file"]
		image = cv2.imread(str(path))
		if image is None:
			raise SystemExit(f"Could not read {path}; check --frames-root")
		return render(image, hole_map, self.cells[key], index, self.status())

	def status(self) -> str:
		s = self.session
		return (
			f"{len(s.labels)} of {len(s.items)} answered\n"
			f"crowded {s.count(ReadinessLabel.CROWDED)}  not yet {s.count(ReadinessLabel.NOT_CROWDED)}  "
			f"empty {s.count(ReadinessLabel.EMPTY)}  unsure {s.count(ReadinessLabel.UNSURE)}"
		)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--frames-root", type=Path, required=True)
	parser.add_argument("--dir", type=Path, default=Path("labels/readiness"))
	parser.add_argument("--hole-maps", type=Path, default=Path("hole_maps"))
	args = parser.parse_args()

	with open(args.dir / "items.csv", encoding="utf-8") as handle:
		items = sorted(csv.DictReader(handle), key=lambda r: int(r["order"]))
	labels_path = args.dir / "labels.csv"
	session = LabelSession(items, "item_id", read_labels(labels_path))
	screens = ItemScreens(args.frames_root, args.hole_maps, session)  # loads the hole maps (fails early if one is bad)
	print(__doc__)
	print(f"{len(session.labels)} answered so far, {len(session.queue)} to go.")
	if not session.queue:
		return
	run_session(session, labels_path, LABELS, screens, WINDOW)
	print(f"Saved {len(session.labels)} answers to {labels_path}.")
	print("Then: uv run python tools/evaluate_readiness.py")


if __name__ == "__main__":
	main()
