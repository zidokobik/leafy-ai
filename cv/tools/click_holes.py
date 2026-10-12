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
from pathlib import Path

import cv2
import numpy as np

from leafy_cv.frames import parse_frame_path
from leafy_cv.hole_map import HoleMap, Zone, camera_number, number_holes, row_problems, zone_problems

WINDOW = "click holes"
ROW_COLOURS = [(66, 135, 245), (245, 170, 66), (80, 200, 120), (200, 90, 220), (240, 220, 70), (90, 220, 230)]
DELETE_RADIUS_PX = 20
FIRST_ZONE_NAME = "canopy_far"


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
	level = int(frame.camera_id.split("_")[0].removeprefix("level"))
	valid_from, valid_to = period_dates(args.periods_csv, frame.camera_id, args.period)
	out_path = args.out_dir / f"{frame.camera_id}_{args.period}.json"

	rows: list[list[tuple[float, float, bool]]] = [[]]
	zones: list[Zone] = []
	notes, board_polygon = "", None
	channel_axis = args.channel_axis or "row"
	if out_path.exists():
		existing = HoleMap.load(out_path)
		notes, zones, board_polygon = existing.notes, list(existing.zones), existing.board_polygon
		channel_axis = existing.channel_axis
		rows = [[] for _ in range(max(h.row for h in existing.holes))] if existing.holes else [[]]
		for hole in existing.holes:
			rows[hole.row - 1].append((hole.x, hole.y, hole.estimated))
		print(f"Editing {out_path}: {len(existing.holes)} holes in {len(rows)} rows, {len(zones)} zones")

	# Always start on row 1, so clicks never land in the last row by accident.
	state = {"row": 0, "estimated": False, "history": [], "dirty": False, "warning": "", "drawing": None}

	def save() -> None:
		holes = number_holes(level, camera_number(frame.camera_id), rows)
		hole_map = HoleMap(
			camera_id=frame.camera_id,
			level=level,
			period=args.period,
			valid_from=valid_from,
			valid_to=valid_to,
			image_size=(width, height),
			reference_file=args.frame.name,
			holes=holes,
			board_polygon=board_polygon,
			notes=notes,
			zones=zones,
			channel_axis=channel_axis,
		)
		hole_map.save(out_path)
		state["dirty"] = False
		print(f"Saved {len(holes)} holes in {sum(1 for r in rows if r)} rows and {len(zones)} zones to {out_path}")
		problems = (row_problems(hole_map) if holes else []) + zone_problems(hole_map)
		state["warning"] = f"CHECK: {problems[0]}" if problems else ""
		for problem in problems:
			print(f"  WARNING: {problem}")

	def on_mouse(event, mx, my, _flags, _param) -> None:
		x, y = mx / args.scale, my / args.scale
		x, y = min(max(x, 0.0), width), min(max(y, 0.0), height)
		if state["drawing"] is not None:
			if event == cv2.EVENT_LBUTTONDOWN:
				state["drawing"].append((int(round(x)), int(round(y))))
			elif event == cv2.EVENT_RBUTTONDOWN and state["drawing"]:
				state["drawing"].pop()
			return
		if event == cv2.EVENT_LBUTTONDOWN:
			rows[state["row"]].append((x, y, state["estimated"]))
			state["history"].append(state["row"])
			state["dirty"] = True
		elif event == cv2.EVENT_RBUTTONDOWN:
			best = None
			for r, row in enumerate(rows):
				for k, (hx, hy, _) in enumerate(row):
					d = np.hypot(hx - x, hy - y)
					if d <= DELETE_RADIUS_PX and (best is None or d < best[0]):
						best = (d, r, k)
			if best is not None:
				rows[best[1]].pop(best[2])
				# switch to that row, so the replacement click lands in the same row (7 Oct: re-placed
				# dots all went into row 1 because the tool stayed on the row it opened on)
				state["row"] = best[1]
				state["dirty"] = True

	def render() -> np.ndarray:
		canvas = image.copy()
		for zone in zones:
			polygon = np.array(zone.polygon, np.int32)
			shade = canvas.copy()
			cv2.fillPoly(shade, [polygon], (255, 255, 255))
			canvas = cv2.addWeighted(canvas, 0.75, shade, 0.25, 0)
			cv2.polylines(canvas, [polygon], True, (255, 255, 255), 2)
			corner = tuple(int(v) for v in polygon.min(axis=0) + (6, 18))
			cv2.putText(canvas, zone.name, corner, cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
		if state["drawing"]:
			points = np.array(state["drawing"], np.int32)
			cv2.polylines(canvas, [points], False, (255, 255, 0), 2)
			for point in state["drawing"]:
				cv2.circle(canvas, point, 4, (255, 255, 0), -1)
		for r, row in enumerate(rows):
			colour = ROW_COLOURS[r % len(ROW_COLOURS)]
			for k, (x, y, estimated) in enumerate(sorted(row, key=lambda p: p[0]), start=1):
				centre = (int(round(x)), int(round(y)))
				cv2.circle(canvas, centre, 6, (0, 0, 0), -1)
				cv2.circle(canvas, centre, 5, (0, 140, 255) if estimated else colour, -1)
				if r == state["row"] and state["drawing"] is None:
					cv2.circle(canvas, centre, 9, (255, 255, 255), 1)
				at = (centre[0] + 7, centre[1] - 7)
				cv2.putText(canvas, f"R{r + 1}H{k}", at, cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)
		canvas = cv2.resize(canvas, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_LINEAR)
		if state["drawing"] is not None:
			status = f"DRAWING ZONE: {len(state['drawing'])} corners  [left click corner, right click undo, z finish]"
		else:
			status = (
				f"row {state['row'] + 1}/{len(rows)}  holes {sum(len(r) for r in rows)}  zones {len(zones)}  "
				f"estimated {'ON' if state['estimated'] else 'off'}  {'*unsaved*' if state['dirty'] else 'saved'}  "
				"[n/p row, e est., u undo, z zone, s save, q save+quit, x quit]"
			)
		cv2.rectangle(canvas, (0, 0), (canvas.shape[1], 24), (0, 0, 0), -1)
		cv2.putText(canvas, status, (8, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
		if state["warning"]:
			cv2.rectangle(canvas, (0, 24), (canvas.shape[1], 48), (0, 0, 180), -1)
			cv2.putText(canvas, state["warning"][:150], (8, 41), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
		return canvas

	cv2.namedWindow(WINDOW, cv2.WINDOW_AUTOSIZE)
	cv2.setMouseCallback(WINDOW, on_mouse)
	while True:
		cv2.imshow(WINDOW, render())
		key = cv2.waitKey(30) & 0xFF
		if key == ord("z"):
			if state["drawing"] is None:
				state["drawing"] = []
			elif len(state["drawing"]) >= 3:
				zones.append(Zone(name=next_zone_name(zones), polygon=tuple(state["drawing"])))
				print(f"Added zone '{zones[-1].name}' with {len(state['drawing'])} corners")
				state["drawing"], state["dirty"] = None, True
			else:
				print("A zone needs at least 3 corners; drawing cancelled.")
				state["drawing"] = None
		elif state["drawing"] is not None:
			pass  # while drawing a zone, only z and the mouse do anything
		elif key == ord("n"):
			if state["row"] == len(rows) - 1:
				rows.append([])
			state["row"] += 1
		elif key == ord("p"):
			state["row"] = max(0, state["row"] - 1)
		elif key == ord("e"):
			state["estimated"] = not state["estimated"]
		elif key == ord("u") and state["history"]:
			row = state["history"].pop()
			if rows[row]:
				rows[row].pop()
				state["dirty"] = True
		elif key == ord("d") and zones:
			print(f"Deleted zone '{zones.pop().name}'")
			state["dirty"] = True
		elif key == ord("s"):
			save()
		elif key in (ord("q"), 27):
			already_warned = state["warning"] and not state["dirty"]
			save()
			if state["warning"] and not already_warned:
				print("  Problems found. Fix them, or press q again to quit anyway.")
				continue
			break
		elif key == ord("x"):
			if state["dirty"]:
				print("Quit without saving; unsaved changes discarded.")
			break
		if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
			if state["dirty"]:
				save()
			break
	cv2.destroyAllWindows()


if __name__ == "__main__":
	main()
