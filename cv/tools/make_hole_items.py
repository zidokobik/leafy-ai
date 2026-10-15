"""Pick hole crops for us to label "crowded or not", to check the frozen readiness rule.

There is no grower round, so we label against the written rule ourselves:
"do this plant's leaves touch the leaves of any neighbouring plant, in the same channel or the next channel?"
Crops must be drawn from statuses made with the current rule.

Usage (from the cv/ folder, after tools/run.py has run on the maps):
	uv run python tools/make_hole_items.py

Sampling (agreed before any labels existed): stratified by camera x CV status, so every camera gets
enough of each status and is reported on its own:
- quotas per camera: ready 32, growing 32, candidate 12, empty 6 (fewer when a camera has fewer);
- 8 ready and 4 growing camera 2 crops from the first two days after the 30 Sep transfer (30 Sep 11:00 - 1 Oct),
  spread over the board's rows: every middle-row plant (rows 3-6) was `ready` from the start, and these crops
  decide whether that was real;
- growing crops spread over contact (so plants just under the crowding line are included), the other
  statuses spread over days;
- at most one crop per hole per day; never a hole outside the frame (edge_of_frame) or a frame used to train
  the plant filter.
Each item gets a split by day (dev/test, kept for reference). Labellers never see the numbers or statuses.
Writes labels/readiness/items.csv (shuffled; same columns as before) and labels/readiness/strata.csv
(per camera and status: hole-days available and picked; evaluate_readiness.py weights by them).
"""

import argparse
import csv
import random
from collections import defaultdict
from pathlib import Path

from leafy_cv.csv_files import read_observations, write_csv
from leafy_cv.readiness import CANDIDATE, EMPTY, GROWING, READY

QUOTAS = {READY: 32, GROWING: 32, CANDIDATE: 12, EMPTY: 6}
EARLY_CAMERA, EARLY_DAYS = "level1_camera2", ("2026-09-30", "2026-10-01")
EARLY_QUOTAS = {READY: 8, GROWING: 4}  # of camera 2's ready / growing quotas
EARLY_FROM = "2026-09-30T11"  # the transfer: earlier 30 Sep frames are the old layout
GROWING_BINS = (0.0, 0.2, 0.35, 0.5, 1.01)  # contact bins the growing crops are spread over


def hole_day(row: dict) -> tuple[str, str, str]:
	return row["camera_id"], row["hole_id"], row["captured_at"][:10]


def is_early(row: dict) -> bool:
	"""Camera 2 in the first two days after the 30 Sep transfer (the days that decide whether `ready` was real)."""
	return (
		row["camera_id"] == EARLY_CAMERA and row["captured_at"] >= EARLY_FROM and row["captured_at"][:10] in EARLY_DAYS
	)


def can_label(row: dict, training_frames: set[str]) -> bool:
	"""A hole row inside the frame, with a status we report and a contact (unless empty), not a training frame."""
	if row["kind"] != "hole" or row["status"] not in QUOTAS or "edge_of_frame" in row["flags"]:
		return False
	if row["image_id"] in training_frames:
		return False
	return row["status"] == EMPTY or row["boundary_contact"] != ""


def read_pool(runs: Path, training_frames: set[str]) -> list[dict]:
	"""Hole rows that can be labelled."""
	return [row for row in read_observations(runs) if can_label(row, training_frames)]


def spread_key(row: dict) -> str:
	if row["status"] == GROWING:
		contact = float(row["boundary_contact"])
		return str(next(k for k in range(len(GROWING_BINS) - 1) if GROWING_BINS[k] <= contact < GROWING_BINS[k + 1]))
	return row["captured_at"][:10]


def round_robin(rows: list[dict], key) -> list[dict]:
	"""rows reordered so consecutive picks cycle through the values of key (each group keeps its order)."""
	groups = defaultdict(list)
	for row in rows:
		groups[key(row)].append(row)
	queues, out = [groups[k] for k in sorted(groups)], []
	while any(queues):
		for queue in queues:
			if queue:
				out.append(queue.pop(0))
	return out


def pick_items(pool: list[dict], rng: random.Random) -> tuple[list[dict], dict]:
	"""Stratified picks and, per (camera, status), (hole-days available, picked)."""
	rows = pool[:]
	rng.shuffle(rows)
	by_stratum = defaultdict(list)
	for row in rows:
		by_stratum[(row["camera_id"], row["status"])].append(row)
	available = {k: len({hole_day(r) for r in v}) for k, v in by_stratum.items()}
	taken, picked, count = set(), [], defaultdict(int)

	def take(row: dict) -> bool:
		key = (row["camera_id"], row["status"])
		if hole_day(row) in taken or count[key] >= QUOTAS[row["status"]]:
			return False
		taken.add(hole_day(row))
		picked.append(row)
		count[key] += 1
		return True

	early = [r for r in rows if is_early(r) and r["status"] in (READY, GROWING)]
	n_early = defaultdict(int)
	for row in round_robin(early, lambda r: r["row"]):  # spread over the board's rows
		if n_early[row["status"]] < EARLY_QUOTAS[row["status"]] and take(row):
			n_early[row["status"]] += 1
	order = {CANDIDATE: 0, EMPTY: 1, READY: 2, GROWING: 3}  # scarce statuses first (they share hole-days)
	for key in sorted(by_stratum, key=lambda k: (k[0], order[k[1]])):
		for row in round_robin(by_stratum[key], spread_key):
			if count[key] >= QUOTAS[key[1]]:
				break
			take(row)
	return picked, {k: (available[k], count[k]) for k in sorted(available)}


def item_id(row: dict) -> str:
	"""camera_period_YYYYMMDD_HHMMSS_holeid (the time comes from the frame file name)."""
	stamp = row["image_id"][-19:-4]  # <camera>_YYYYMMDD_HHMMSS.jpg -> YYYYMMDD_HHMMSS
	return f"{row['camera_id']}_{row['period']}_{stamp}_{row['hole_id']}"


def make_items(picked: list[dict], rng: random.Random) -> list[dict]:
	"""items.csv rows in a shuffled labelling order, each with a dev/test split by day (alternating days)."""
	days = sorted({row["captured_at"][:10] for row in picked})
	split_of = {day: ("dev" if i % 2 == 0 else "test") for i, day in enumerate(days)}
	ordered = picked[:]
	rng.shuffle(ordered)
	return [
		{
			"item_id": item_id(row),
			"camera_id": row["camera_id"],
			"period": row["period"],
			"file": row["image_id"],
			"captured_at": row["captured_at"],
			"hole_id": row["hole_id"],
			"split": split_of[row["captured_at"][:10]],
			"order": n,
		}
		for n, row in enumerate(ordered)
	]


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--runs", type=Path, default=Path("data/runs"))
	parser.add_argument("--filter-labels", type=Path, default=Path("labels/plant_masks/candidates.csv"))
	parser.add_argument("--out", type=Path, default=Path("labels/readiness/items.csv"))
	parser.add_argument("--seed", type=int, default=0)
	args = parser.parse_args()

	if args.out.exists():
		raise SystemExit(f"{args.out} exists; labels may refer to it. Use another --out to make a new set.")
	with open(args.filter_labels, encoding="utf-8") as handle:
		training_frames = {row["file"] for row in csv.DictReader(handle)}
	pool = read_pool(args.runs, training_frames)
	if not pool:
		raise SystemExit(f"No observations under {args.runs}; run tools/run.py first")

	rng = random.Random(args.seed)
	picked, strata = pick_items(pool, rng)
	items = make_items(picked, rng)
	args.out.parent.mkdir(parents=True, exist_ok=True)
	write_csv(args.out, list(items[0]), items)
	strata_rows = [
		{"camera_id": camera, "status": status, "hole_days_available": available, "picked": n}
		for (camera, status), (available, n) in strata.items()
	]
	write_csv(args.out.parent / "strata.csv", ["camera_id", "status", "hole_days_available", "picked"], strata_rows)
	print(f"Wrote {len(items)} items to {args.out} (strata in {args.out.parent / 'strata.csv'}):")
	for (camera, status), (available, n) in strata.items():
		print(f"  {camera} {status}: {n} of {available} hole-days")
	print(f"  {EARLY_CAMERA} on {', '.join(EARLY_DAYS)}: {sum(is_early(i) for i in items)}")
	print("Next: uv run python tools/label_holes.py --frames-root <frames folder>")


if __name__ == "__main__":
	main()
