"""Score the frozen readiness rule against our own labels (tools/label_holes.py).

Usage (from the cv/ folder):
	uv run python tools/evaluate_readiness.py

Agreed 11 Oct, before any labels existed: the rules and thresholds are frozen
(metrics-v3, rule-v5 = rule-v4 with contact in both directions, corrected 12 Oct before these labels) and are NOT
changed after seeing these results; anything that looks wrong goes into the
limitations and future scope. Because nothing is tuned, all labelled crops are scored (the test half is shown too).

Reported per camera, never as one pooled number (camera 3 is the other crop):
1. Per CV status (ready, candidate, growing, empty): how many crops, and the share a human called crowded,
   with a 95% Wilson interval. For `ready` that share is how often the grower alert is right.
2. Crowded plants caught versus missed: of the crops a human called crowded, how many the CV had `ready`
   (the grower alert) and how many it had growing or empty (missed), as counts and as a catch rate
   weighted back to how common each status is (the crops are stratified, labels/readiness/strata.csv),
   with a 95% interval (Jeffreys draws per status).
3. Empty: how often a human answered "empty" for CV-empty crops, and the reverse.
"Unsure" answers are counted and left out. A threshold sweep on raw contact (dev days) is printed as a finding
for future work only.

Writes data/checks/readiness_eval_items.csv (every labelled crop with its numbers, for looking at mistakes).
"""

import argparse
import csv
import math
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from leafy_cv.csv_files import write_csv

STATUSES = ("ready", "candidate", "growing", "empty")
MISSED = ("growing", "empty")  # a crowded plant with these statuses gets no alert
BOOTSTRAP = 2000
THRESHOLDS = np.round(np.arange(0.20, 0.81, 0.05), 2)


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
	"""95% Wilson interval for k of n."""
	if n == 0:
		return float("nan"), float("nan")
	p = k / n
	centre = (p + z * z / (2 * n)) / (1 + z * z / n)
	half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
	return max(0.0, centre - half), min(1.0, centre + half)


def weighted_catch(crowded: dict[str, int], weights: dict[str, float], caught: tuple[str, ...]) -> float:
	"""Share of crowded plants (weighted to the population) whose status is in `caught`."""
	total = sum(weights.get(s, 0.0) * n for s, n in crowded.items())
	hit = sum(weights.get(s, 0.0) * n for s, n in crowded.items() if s in caught)
	return hit / total if total else float("nan")


def catch_interval(rows: list[dict], weights: dict[str, float], caught: tuple[str, ...], seed: int = 0):
	"""95% interval of weighted_catch: each status's crowded share drawn from its Jeffreys Beta(k+0.5, n-k+0.5)
	(so a status where every crop agreed still carries its uncertainty), then weighted as in weighted_catch."""
	rng = np.random.default_rng(seed)
	counts = defaultdict(lambda: [0, 0])
	for row in rows:
		counts[row["status"]][0] += row["label"] == "crowded"
		counts[row["status"]][1] += 1
	values = []
	for _ in range(BOOTSTRAP):
		share = {s: rng.beta(k + 0.5, n - k + 0.5) for s, (k, n) in counts.items()}
		total = sum(weights.get(s, 0.0) * counts[s][1] * share[s] for s in counts)
		hit = sum(weights.get(s, 0.0) * counts[s][1] * share[s] for s in counts if s in caught)
		values.append(hit / total if total else float("nan"))
	return tuple(np.nanpercentile(values, [2.5, 97.5]))


def camera_report(rows: list[dict], weights: dict[str, float]) -> dict:
	"""Numbers for one camera: rows are its judged crops (label crowded / not_crowded)."""
	out = {"status": {}}
	for status in STATUSES:
		part = [r for r in rows if r["status"] == status]
		k = sum(r["label"] == "crowded" for r in part)
		out["status"][status] = (k, len(part), *wilson(k, len(part)))
	crowded = Counter(r["status"] for r in rows if r["label"] == "crowded")
	out["caught"] = crowded["ready"]
	out["candidate"] = crowded["candidate"]
	out["missed"] = sum(crowded[s] for s in MISSED)
	out["catch"] = weighted_catch(dict(crowded), weights, ("ready",))
	out["catch_ci"] = catch_interval(rows, weights, ("ready",))
	out["catch_with_candidate"] = weighted_catch(dict(crowded), weights, ("ready", "candidate"))
	return out


def print_report(title: str, rows: list[dict], weights: dict[tuple[str, str], float]) -> None:
	print(f"\n=== {title} ===")
	for camera in sorted({r["camera_id"] for r in rows}):
		part = [r for r in rows if r["camera_id"] == camera]
		judged = [r for r in part if r["label"] in ("crowded", "not_crowded")]
		w = {s: weights.get((camera, s), 1.0) for s in STATUSES}
		report = camera_report(judged, w)
		extra = Counter(r["label"] for r in part if r["label"] not in ("crowded", "not_crowded"))
		print(f"{camera}: {len(judged)} judged crops (also: {dict(extra) or 'none'})")
		for status, (k, n, lo, hi) in report["status"].items():
			if n:
				print(f"  CV {status:9} {n:3} crops, human says crowded {k:3} = {k / n:5.1%} [{lo:.0%}-{hi:.0%}]")
		lo, hi = report["catch_ci"]
		print(
			f"  crowded plants: caught (CV ready) {report['caught']}, candidate {report['candidate']}, "
			f"missed (growing/empty) {report['missed']}; catch rate weighted to the population "
			f"{report['catch']:.1%} [{lo:.0%}-{hi:.0%}] (with candidate {report['catch_with_candidate']:.1%})"
		)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--dir", type=Path, default=Path("labels/readiness"))
	parser.add_argument("--runs", type=Path, default=Path("data/runs"))
	parser.add_argument("--out", type=Path, default=Path("data/checks/readiness_eval_items.csv"))
	args = parser.parse_args()

	with open(args.dir / "items.csv", encoding="utf-8") as handle:
		items = {row["item_id"]: row for row in csv.DictReader(handle)}
	with open(args.dir / "labels.csv", encoding="utf-8") as handle:
		labels = list(csv.DictReader(handle))
	if not labels:
		raise SystemExit(f"No labels yet in {args.dir / 'labels.csv'}: run tools/label_holes.py first")
	unknown = [row["item_id"] for row in labels if row["item_id"] not in items]
	if unknown:  # answers to another crop set (e.g. the 7 Oct question) must never be scored against this one
		raise SystemExit(f"{len(unknown)} labels are for items not in items.csv (another crop set?), e.g. {unknown[0]}")
	weights = {}
	with open(args.dir / "strata.csv", encoding="utf-8") as handle:
		for row in csv.DictReader(handle):
			if int(row["picked"]):
				weights[(row["camera_id"], row["status"])] = int(row["hole_days_available"]) / int(row["picked"])
	observations = {}
	for path in args.runs.glob("*/observations.csv"):
		with open(path, encoding="utf-8") as handle:
			for row in csv.DictReader(handle):
				observations[(row["camera_id"], row["period"], row["image_id"], row["hole_id"])] = row

	rows = []
	for label in labels:
		item = items[label["item_id"]]
		obs = observations.get((item["camera_id"], item["period"], item["file"], item["hole_id"]))
		if obs is None:
			raise SystemExit(f"No measurement for {label['item_id']}: run tools/run.py on its map first")
		rows.append(
			{
				**item,
				"label": label["label"],
				"coverage": obs["coverage"],
				"boundary_contact": obs["boundary_contact"],
				"status": obs["status"],
			}
		)
	print(f"{len(rows)} labels: " + ", ".join(f"{k} {v}" for k, v in Counter(r["label"] for r in rows).most_common()))
	print("Rules frozen (metrics-v3, rule-v5): these numbers are reported as they are, nothing is tuned on them.")

	print_report("All labelled crops (the main result)", rows, weights)
	print_report("Test days only (for reference)", [r for r in rows if r["split"] == "test"], weights)

	print("\n=== Empty ===")
	for camera in sorted({r["camera_id"] for r in rows}):
		part = [r for r in rows if r["camera_id"] == camera]
		cv_empty = [r for r in part if r["status"] == "empty"]
		said_empty = [r for r in part if r["label"] == "empty"]
		human_empty_of_cv = sum(r["label"] == "empty" for r in cv_empty)
		cv_empty_of_human = sum(r["status"] == "empty" for r in said_empty)
		print(
			f"{camera}: CV empty {len(cv_empty)}, of which human 'empty' {human_empty_of_cv}; "
			f"human 'empty' {len(said_empty)}, of which CV empty {cv_empty_of_human}"
		)

	dev = [r for r in rows if r["split"] == "dev" and r["label"] in ("crowded", "not_crowded")]
	if dev:
		truth = np.array([r["label"] == "crowded" for r in dev])
		contact = np.array([float(r["boundary_contact"] or "nan") for r in dev])
		print("\nFinding only (not applied): raw contact threshold on dev days -> agreement with labels")
		for threshold in THRESHOLDS:
			print(f"  {threshold:.2f}  {np.mean((contact >= threshold) == truth):.1%}")

	args.out.parent.mkdir(parents=True, exist_ok=True)
	write_csv(args.out, list(rows[0]), rows)
	print(f"\nWrote {args.out}")


if __name__ == "__main__":
	main()
