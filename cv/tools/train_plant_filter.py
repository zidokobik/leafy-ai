"""Train the plant filter from the labelled outlines and report how well it works.

Usage (from the cv/ folder, after labelling with tools/label_masks.py):
	uv run python tools/train_plant_filter.py --frames-root E:\\Claude

How it's checked: the labelled frames are split into 5 groups; each group is predicted by a
model trained on the other 4 ("grouped cross-validation"). Outlines from the same frame never
sit on both sides, so the score reflects frames the model hasn't seen. It's the honest number
to report.

Writes trained/plant_filter.json (tracked by git; small) and
data/checks/plant_filter_errors.jpg: the outlines it got most wrong, to look at.
Only "plant" and "not plant" answers train it; "mixed" and "skip" are counted, not used.
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from leafy_cv.drawing import dim_outside, put_outlined_text
from leafy_cv.plant_filter import FEATURE_NAMES, PlantFilter, mask_features, unpack_masks

MIN_LABELS = 100
FOLDS = 5
ERROR_TILES = 24


# C=10 (light regularisation) was chosen on 5 Oct by the same grouped cross-validation, using
# Pearl's 632 labels: 97.4% vs 96.5% at C=1, with the biggest gain on camera 2's pale pink-lit
# leaves. Pairwise features (98.3%) and a random forest (98.1%) were not worth the complexity.
C = 10.0


def model() -> Pipeline:
	return make_pipeline(StandardScaler(), LogisticRegression(C=C, class_weight="balanced", max_iter=5000))


def error_sheet(rows: list[dict], images: dict[str, np.ndarray], masks: dict[str, np.ndarray], out: Path) -> None:
	tiles = []
	for row in rows[:ERROR_TILES]:
		image = images[row["file"]]
		mask = masks[row["candidate_id"]]
		x0, y0, x1, y1 = (int(v) for v in row["bbox"].split())
		pad = 20
		x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
		x1, y1 = min(image.shape[1], x1 + pad), min(image.shape[0], y1 + pad)
		lit = dim_outside(image, mask)
		tile = cv2.resize(lit[y0:y1, x0:x1], (200, 160))
		text = f"said {row['label']}, p(plant) {row['p']:.2f}"
		put_outlined_text(tile, text, (4, 154), 0.4)
		tiles.append(tile)
	if not tiles:
		return
	while len(tiles) % 6:
		tiles.append(np.zeros_like(tiles[0]))
	sheet = np.vstack([np.hstack(tiles[i : i + 6]) for i in range(0, len(tiles), 6)])
	out.parent.mkdir(parents=True, exist_ok=True)
	cv2.imwrite(str(out), sheet)


def read_answers(labels_dir: Path) -> tuple[dict[str, dict], list[dict]]:
	"""The candidates by id, and the plant / not plant answers (mixed and skip are counted, not used)."""
	with open(labels_dir / "candidates.csv", encoding="utf-8") as handle:
		candidates = {row["candidate_id"]: row for row in csv.DictReader(handle)}
	with open(labels_dir / "labels.csv", encoding="utf-8") as handle:
		answers = list(csv.DictReader(handle))
	counts = Counter(a["label"] for a in answers)
	print(f"{len(answers)} answers: " + ", ".join(f"{k} {v}" for k, v in counts.most_common()))
	used = [a for a in answers if a["label"] in ("plant", "not_plant")]
	if len(used) < MIN_LABELS:
		raise SystemExit(f"Need at least {MIN_LABELS} plant / not plant answers; have {len(used)}.")
	if counts["mixed"] / max(len(answers), 1) > 0.15:
		print("  Note: over 15% mixed. MobileSAM often outlines plant and board together; check the prompts.")
	return candidates, used


def load_examples(
	used: list[dict], candidates: dict[str, dict], frames_root: Path, masks_path: Path
) -> tuple[list[dict], dict[str, np.ndarray], dict[str, np.ndarray], np.ndarray]:
	"""Per answer: its candidate row (+ label) and features; also the frames and outlines (for the error sheet)."""
	images, masks, rows, features = {}, {}, [], []
	with np.load(masks_path) as packed:
		for answer in used:
			row = {**candidates[answer["candidate_id"]], "label": answer["label"]}
			if row["file"] not in images:
				image = cv2.imread(str(frames_root / row["camera_id"] / row["file"]))
				if image is None:
					raise SystemExit(f"Could not read {row['file']}; check --frames-root")
				images[row["file"]] = image
			mask = unpack_masks(packed[row["candidate_id"]], int(row["width"]))[int(row["best"])]
			masks[row["candidate_id"]] = mask
			features.append(mask_features(images[row["file"]], mask))
			rows.append(row)
	return rows, images, masks, np.array(features)


def cross_validate(rows: list[dict], x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
	"""P(plant) of every example from a model that never saw its frame, and the accuracy; prints the report."""
	groups = np.array([row["file"] for row in rows])
	folds = min(FOLDS, len(set(groups)))
	p = cross_val_predict(model(), x, y, groups=groups, cv=GroupKFold(folds), method="predict_proba")[:, 1]
	predicted = p >= 0.5
	tp, fp = int((predicted & y).sum()), int((predicted & ~y).sum())
	fn, tn = int((~predicted & y).sum()), int((~predicted & ~y).sum())
	print(f"\nChecked on unseen frames ({folds}-fold grouped cross-validation, {len(set(groups))} frames):")
	print(f"  accuracy  {(tp + tn) / len(y):.1%}  ({tp + tn} of {len(y)})")
	print(f"  plant outlines kept      {tp / max(tp + fn, 1):.1%}  (recall; missed {fn})")
	print(f"  kept outlines that are plant {tp / max(tp + fp, 1):.1%}  (precision; wrongly kept {fp})")
	print("  by camera:")
	for camera in sorted({row["camera_id"] for row in rows}):
		pick = np.array([row["camera_id"] == camera for row in rows])
		print(f"    {camera}: {(predicted[pick] == y[pick]).mean():.1%} of {pick.sum()}")
	return p, (tp + tn) / len(y)


def save_filter(x: np.ndarray, y: np.ndarray, accuracy: float, out: Path) -> None:
	"""Fit on all examples and save the plant filter as plain JSON."""
	final = model().fit(x, y)
	scaler, logistic = final[0], final[1]
	PlantFilter(
		feature_names=FEATURE_NAMES,
		mean=scaler.mean_,
		scale=scaler.scale_,
		weights=logistic.coef_[0],
		bias=float(logistic.intercept_[0]),
		notes=f"{len(y)} labels ({int(y.sum())} plant), grouped CV accuracy {accuracy:.3f}",
	).save(out)
	print(f"\nSaved {out}")


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
	parser.add_argument("--frames-root", type=Path, required=True)
	parser.add_argument("--dir", type=Path, default=Path("labels/plant_masks"))
	parser.add_argument("--out", type=Path, default=Path("trained/plant_filter.json"))
	parser.add_argument("--errors", type=Path, default=Path("data/checks/plant_filter_errors.jpg"))
	args = parser.parse_args()

	candidates, used = read_answers(args.dir)
	rows, images, masks, x = load_examples(used, candidates, args.frames_root, args.dir / "masks.npz")
	y = np.array([row["label"] == "plant" for row in rows])
	p, accuracy = cross_validate(rows, x, y)
	save_filter(x, y, accuracy, args.out)

	wrong = [{**row, "p": float(pi)} for row, pi, ok in zip(rows, p, (p >= 0.5) == y, strict=True) if not ok]
	wrong.sort(key=lambda r: -abs(r["p"] - 0.5))
	error_sheet(wrong, images, masks, args.errors)
	if wrong:
		print(f"Most confident mistakes ({len(wrong)} in total): {args.errors}")


if __name__ == "__main__":
	main()
