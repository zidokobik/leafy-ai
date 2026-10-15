"""Click hole centres (and outline canopy zones) on one frame to make or correct a hole map.

Usage (from the cv/ folder):
	uv run python tools/click_holes.py --period P2 `
		--frame E:\\Claude\\level1_camera2\\level1_camera2_20260922_130030.jpg

If hole_maps/<camera_id>_<period>.json already exists it is opened for editing; its zones and
notes are kept. The period's dates are read from data/periods.csv (run build_frame_index.py first).

Rows are numbered by distance from the camera: click the row FARTHEST from the camera first
(row 1) and the nearest row last. Within a row the order doesn't matter. Every click goes into
the row shown in the status bar (it opens on row 1). Press n before clicking the next row.
To move a dot: right click it (the tool switches to that dot's row), then left click the right spot.

Holes mode (default):
	left click    add a hole to the current row
	right click   delete the nearest hole and switch to its row
	n / p         next / previous row
	e             toggle "estimated" for new clicks (holes hidden under leaves: orange)
	u             undo the last added hole

Zones (a closed canopy where plant bases can't be seen; measured as a whole, not per hole):
	z             start a zone, click its corners, press z again to finish (3+ corners)
	right click   (while drawing) remove the last corner
	d             delete the most recently added zone

Always:
	s             save (rows that don't line up and invalid zones are reported in red)
	q or Esc      save and quit
	x             quit without saving
"""

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from leafy_cv.drawing import ROW_PALETTE
from leafy_cv.frames import Frame, parse_frame_path
from leafy_cv.hole_map import HoleMap, Zone, camera_number, level_number, number_holes, row_problems, zone_problems

WINDOW = "click holes"
DELETE_RADIUS_PX = 20
FIRST_ZONE_NAME = "canopy_far"
# What the key loop does after a key: carry on, redraw at once (skip the window-closed check), or stop.
GO, AGAIN, STOP = "go", "again", "stop"

Point = tuple[float, float, bool]  # a clicked hole centre: x, y, estimated


def period_dates(periods_csv: Path, camera_id: str, period: str) -> tuple[str, str | None]:
	"""Start and end of a period. The camera's latest period has no end (None): its layout is the
	current one, so the map must keep applying to frames that arrive later."""
	if not periods_csv.exists():
		raise SystemExit(f"{periods_csv} not found: run tools/build_frame_index.py first")
	with open(periods_csv, encoding="utf-8") as handle:
		rows = [row for row in csv.DictReader(handle) if row["camera_id"] == camera_id]
	for i, row in enumerate(rows):
		if row["period"] == period:
			latest = i == len(rows) - 1
			return row["start"], None if latest else row["end"]
	raise SystemExit(f"No period {period} for {camera_id} in {periods_csv}")


def next_zone_name(zones: list[Zone]) -> str:
	names = {zone.name for zone in zones}
	if FIRST_ZONE_NAME not in names:
		return FIRST_ZONE_NAME
	n = 2
	while f"canopy_{n}" in names:
		n += 1
	return f"canopy_{n}"


@dataclass
class MapTarget:
	"""Where and for what the clicks are saved."""

	frame: Frame
	frame_file: str
	period: str
	valid_from: str
	valid_to: str | None
	out_path: Path
	image_size: tuple[int, int]  # (width, height)


class HoleClicker:
	"""The click tool's state (rows of clicked holes, zones, the current row and mode) and its actions."""

	def __init__(self, image: np.ndarray, target: MapTarget, scale: float, channel_axis: str):
		self.image, self.target, self.scale = image, target, scale
		self.rows: list[list[Point]] = [[]]
		self.zones: list[Zone] = []
		self.notes, self.board_polygon, self.channel_axis = "", None, channel_axis
		self.row = 0  # always start on row 1, so clicks never land in the last row by accident
		self.estimated = False
		self.history: list[tuple[int, Point]] = []  # holes added this session, oldest first: (row, point)
		self.dirty = False
		self.warning = ""
		self.drawing: list[tuple[int, int]] | None = None  # corners of the zone being drawn
		self.keys = {
			ord("n"): self.next_row,
			ord("p"): self.previous_row,
			ord("e"): self.toggle_estimated,
			ord("u"): self.undo,
			ord("d"): self.delete_zone,
			ord("s"): self.save_key,
			ord("q"): self.save_and_quit,
			27: self.save_and_quit,
			ord("x"): self.quit_without_saving,
		}

	def load(self, existing: HoleMap) -> None:
		"""Open an existing map for editing: its holes by row, zones, notes, board outline and channel axis."""
		self.notes, self.zones, self.board_polygon = existing.notes, list(existing.zones), existing.board_polygon
		self.channel_axis = existing.channel_axis
		self.rows = [[] for _ in range(max(h.row for h in existing.holes))] if existing.holes else [[]]
		for hole in existing.holes:
			self.rows[hole.row - 1].append((hole.x, hole.y, hole.estimated))
		print(
			f"Editing {self.target.out_path}: {len(existing.holes)} holes in {len(self.rows)} rows, "
			f"{len(self.zones)} zones"
		)

	def hole_map(self) -> HoleMap:
		t = self.target
		holes = number_holes(level_number(t.frame.camera_id), camera_number(t.frame.camera_id), self.rows)
		return HoleMap(
			camera_id=t.frame.camera_id,
			level=level_number(t.frame.camera_id),
			period=t.period,
			valid_from=t.valid_from,
			valid_to=t.valid_to,
			image_size=t.image_size,
			reference_file=t.frame_file,
			holes=holes,
			board_polygon=self.board_polygon,
			notes=self.notes,
			zones=self.zones,
			channel_axis=self.channel_axis,
		)

	def save(self) -> None:
		hole_map = self.hole_map()
		hole_map.save(self.target.out_path)
		self.dirty = False
		rows = sum(1 for r in self.rows if r)
		print(f"Saved {len(hole_map.holes)} holes in {rows} rows and {len(self.zones)} zones to {self.target.out_path}")
		problems = (row_problems(hole_map) if hole_map.holes else []) + zone_problems(hole_map)
		self.warning = f"CHECK: {problems[0]}" if problems else ""
		for problem in problems:
			print(f"  WARNING: {problem}")

	# --- mouse

	def on_mouse(self, event: int, mx: int, my: int, _flags, _param) -> None:
		width, height = self.target.image_size
		x, y = min(max(mx / self.scale, 0.0), width), min(max(my / self.scale, 0.0), height)
		if self.drawing is not None:
			if event == cv2.EVENT_LBUTTONDOWN:
				self.drawing.append((round(x), round(y)))
			elif event == cv2.EVENT_RBUTTONDOWN and self.drawing:
				self.drawing.pop()
		elif event == cv2.EVENT_LBUTTONDOWN:
			point = (x, y, self.estimated)
			self.rows[self.row].append(point)
			self.history.append((self.row, point))
			self.dirty = True
		elif event == cv2.EVENT_RBUTTONDOWN:
			self.delete_nearest(x, y)

	def delete_nearest(self, x: float, y: float) -> None:
		"""Delete the hole nearest (x, y) within DELETE_RADIUS_PX and switch to its row, so the replacement click
		lands in the same row (otherwise re-placed dots all go into the row the tool is on)."""
		best = None
		for r, row in enumerate(self.rows):
			for k, (hx, hy, _) in enumerate(row):
				d = np.hypot(hx - x, hy - y)
				if d <= DELETE_RADIUS_PX and (best is None or d < best[0]):
					best = (d, r, k)
		if best is not None:
			self.rows[best[1]].pop(best[2])
			self.row = best[1]
			self.dirty = True

	# --- keys

	def handle_key(self, key: int) -> str:
		if key == ord("z"):
			self.zone_key()
			return GO
		if self.drawing is not None:
			return GO  # while drawing a zone, only z and the mouse do anything
		action = self.keys.get(key)
		return action() if action else GO

	def zone_key(self) -> None:
		"""z starts a zone; z again finishes it (3+ corners) or cancels it."""
		if self.drawing is None:
			self.drawing = []
		elif len(self.drawing) >= 3:
			self.zones.append(Zone(name=next_zone_name(self.zones), polygon=tuple(self.drawing)))
			print(f"Added zone '{self.zones[-1].name}' with {len(self.drawing)} corners")
			self.drawing, self.dirty = None, True
		else:
			print("A zone needs at least 3 corners; drawing cancelled.")
			self.drawing = None

	def next_row(self) -> str:
		if self.row == len(self.rows) - 1:
			self.rows.append([])
		self.row += 1
		return GO

	def previous_row(self) -> str:
		self.row = max(0, self.row - 1)
		return GO

	def toggle_estimated(self) -> str:
		self.estimated = not self.estimated
		return GO

	def undo(self) -> str:
		"""Undo the newest hole added this session: one press per added hole, newest first. If that hole was already
		deleted with a right click, nothing else is removed (press u again for the one before), and holes loaded from
		the map are never undone."""
		if self.history:
			row, point = self.history.pop()
			for k in range(len(self.rows[row]) - 1, -1, -1):
				if self.rows[row][k] is point:
					del self.rows[row][k]
					self.dirty = True
					break
		return GO

	def delete_zone(self) -> str:
		if self.zones:
			print(f"Deleted zone '{self.zones.pop().name}'")
			self.dirty = True
		return GO

	def save_key(self) -> str:
		self.save()
		return GO

	def save_and_quit(self) -> str:
		"""Save and quit; if the save finds new problems, stay open once so they can be fixed (q again quits)."""
		already_warned = self.warning and not self.dirty
		self.save()
		if self.warning and not already_warned:
			print("  Problems found. Fix them, or press q again to quit anyway.")
			return AGAIN
		return STOP

	def quit_without_saving(self) -> str:
		if self.dirty:
			print("Quit without saving; unsaved changes discarded.")
		return STOP

	# --- drawing

	def render(self) -> np.ndarray:
		canvas = self.draw_zones(self.image.copy())
		self.draw_holes(canvas)
		canvas = cv2.resize(canvas, None, fx=self.scale, fy=self.scale, interpolation=cv2.INTER_LINEAR)
		self.draw_status(canvas)
		return canvas

	def draw_zones(self, canvas: np.ndarray) -> np.ndarray:
		for zone in self.zones:
			polygon = np.array(zone.polygon, np.int32)
			shade = canvas.copy()
			cv2.fillPoly(shade, [polygon], (255, 255, 255))
			canvas = cv2.addWeighted(canvas, 0.75, shade, 0.25, 0)
			cv2.polylines(canvas, [polygon], True, (255, 255, 255), 2)
			corner = tuple(int(v) for v in polygon.min(axis=0) + (6, 18))
			cv2.putText(canvas, zone.name, corner, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
		if self.drawing:
			cv2.polylines(canvas, [np.array(self.drawing, np.int32)], False, (255, 255, 0), 2)
			for point in self.drawing:
				cv2.circle(canvas, point, 4, (255, 255, 0), -1)
		return canvas

	def draw_holes(self, canvas: np.ndarray) -> None:
		for r, row in enumerate(self.rows):
			colour = ROW_PALETTE[r % len(ROW_PALETTE)]
			for k, (x, y, estimated) in enumerate(sorted(row, key=lambda p: p[0]), start=1):
				centre = (round(x), round(y))
				cv2.circle(canvas, centre, 6, (0, 0, 0), -1)
				cv2.circle(canvas, centre, 5, (0, 140, 255) if estimated else colour, -1)
				if r == self.row and self.drawing is None:
					cv2.circle(canvas, centre, 9, (255, 255, 255), 1)
				at = (centre[0] + 7, centre[1] - 7)
				cv2.putText(canvas, f"R{r + 1}H{k}", at, cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

	def draw_status(self, canvas: np.ndarray) -> None:
		if self.drawing is not None:
			status = f"DRAWING ZONE: {len(self.drawing)} corners  [left click corner, right click undo, z finish]"
		else:
			holes = sum(len(r) for r in self.rows)
			status = (
				f"row {self.row + 1}/{len(self.rows)}  holes {holes}  zones {len(self.zones)}  "
				f"estimated {'ON' if self.estimated else 'off'}  {'*unsaved*' if self.dirty else 'saved'}  "
				"[n/p row, e est., u undo, z zone, s save, q save+quit, x quit]"
			)
		cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 24), (0, 0, 0), -1)
		cv2.putText(canvas, status, (8, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
		if self.warning:
			cv2.rectangle(canvas, (0, 24), (canvas.shape[1], 48), (0, 0, 180), -1)
			cv2.putText(canvas, self.warning[:150], (8, 41), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)


def run_window(clicker: HoleClicker) -> None:
	cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
	cv2.setMouseCallback(WINDOW, clicker.on_mouse)
	while True:
		cv2.imshow(WINDOW, clicker.render())
		outcome = clicker.handle_key(cv2.waitKey(30) & 0xFF)
		if outcome == STOP:
			break
		if outcome == AGAIN:
			continue
		if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
			if clicker.dirty:
				clicker.save()
			break
	cv2.destroyAllWindows()


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--frame", type=Path, required=True, help="reference frame to click on")
	parser.add_argument("--period", required=True, help="period id from data/periods.csv, e.g. P2")
	parser.add_argument("--periods-csv", type=Path, default=Path("data/periods.csv"))
	parser.add_argument("--out-dir", type=Path, default=Path("hole_maps"))
	parser.add_argument("--scale", type=float, default=1.5, help="display zoom; clicks are converted back")
	parser.add_argument(
		"--channel-axis",
		choices=("row", "col"),
		default=None,
		help="new maps only: 'row' if the channels run left-right in this view (cameras 1, 2), "
		"'col' if the camera looks along them (camera 3). An existing map keeps its own.",
	)
	args = parser.parse_args()

	frame = parse_frame_path(args.frame)
	if frame is None:
		raise SystemExit(f"Not a camera frame name: {args.frame.name}")
	image = cv2.imread(str(args.frame))
	if image is None:
		raise SystemExit(f"Could not read {args.frame}")
	height, width = image.shape[:2]
	valid_from, valid_to = period_dates(args.periods_csv, frame.camera_id, args.period)
	out_path = args.out_dir / f"{frame.camera_id}_{args.period}.json"
	target = MapTarget(frame, args.frame.name, args.period, valid_from, valid_to, out_path, (width, height))
	clicker = HoleClicker(image, target, args.scale, args.channel_axis or "row")
	if out_path.exists():
		clicker.load(HoleMap.load(out_path))
	run_window(clicker)


if __name__ == "__main__":
	main()
