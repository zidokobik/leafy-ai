"""Measure how far a camera moved between two frames, and whether the scene changed.

Camera position (is the camera where it was?):
1. Find distinctive corners (ORB keypoints) in each frame, only inside the camera's fixed
   parts (frame rails, walls, light bar; listed in config/fixed_parts.json). Growing or
   swaying leaves can then never look like a camera move. Contrast equalisation (CLAHE) first,
   so the same corner looks alike in both frames.
2. Match corners between the frames by their descriptors.
3. Fit the shift + rotation that explains the most matches. RANSAC ignores matches that
   disagree. The matches it keeps are the "inliers".

Scene (is the layout what it was?): the fixed parts can't see plants being moved, so a second
measure compares where the plants are (see scene.py): the share of the frame that switched
between plant and not plant ("plant_change").

stable = enough inliers, shift <= 5 px, and plant_change <= 0.045.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

MAX_FEATURES = 2000
MAX_MATCHES = 400
RANSAC_THRESHOLD_PX = 2.5
FAST_THRESHOLD = 7  # lower than ORB's default 20: the fixed parts are small, so take fainter corners too
# From the 30 Sep audit: normal consecutive frames move under 1 px; camera 1's first frame of
# the day moves ~8 px; a real bump (camera 3, 18 Sep) moved 22 px with 333 inliers on fixed parts.
MIN_INLIERS = 15
MAX_STABLE_SHIFT_PX = 5.0
MIN_INLIERS_TO_CALL_A_MOVE = 50
# From all 684 frames (5 Oct), plant change with a one-tile tolerance (scene.plant_change):
# the 7 real layout events 0.060-0.479; normal hours at most 0.034; overnight at most 0.028.
# The limit sits midway between normal and the weakest event (camera 1, 30 Sep 11:00, where
# plants were swapped for other plants in similar places). The margin is real but not wide.
MAX_PLANT_CHANGE = 0.045

Rect = tuple[int, int, int, int]
DEFAULT_FIXED_PARTS = Path(__file__).resolve().parents[2] / "config" / "fixed_parts.json"


@dataclass(frozen=True)
class Features:
	keypoints: tuple
	descriptors: np.ndarray | None


@dataclass(frozen=True)
class Alignment:
	inliers: int
	shift_px: float | None = None
	rotation_deg: float | None = None
	plant_change: float | None = None  # share of the frame that switched plant <-> not plant

	@property
	def aligned(self) -> bool:
		"""Enough agreeing matches to trust the measured shift."""
		return self.inliers >= MIN_INLIERS and self.shift_px is not None

	@property
	def stable(self) -> bool:
		"""Aligned, the camera hasn't moved meaningfully, and the plants are where they were."""
		same_scene = self.plant_change is None or self.plant_change <= MAX_PLANT_CHANGE
		return self.aligned and self.shift_px <= MAX_STABLE_SHIFT_PX and same_scene

	@property
	def clear_move(self) -> bool:
		"""The fixed parts agree the camera itself moved."""
		return (
			self.inliers >= MIN_INLIERS_TO_CALL_A_MOVE
			and self.shift_px is not None
			and self.shift_px > MAX_STABLE_SHIFT_PX
		)


def load_fixed_parts(path: Path = DEFAULT_FIXED_PARTS) -> dict[str, list[Rect]]:
	data = json.loads(Path(path).read_text(encoding="utf-8"))
	return {camera: [tuple(r) for r in rects] for camera, rects in data.items() if not camera.startswith("_")}


def feature_mask(shape: tuple[int, int], regions: Sequence[Rect] | None = None) -> np.ndarray:
	"""Where to look for corners: the fixed parts if given, else the whole frame.

	Either way, skip the timestamp strip along the top and the watermark bottom-right.
	"""
	height, width = shape
	if regions:
		mask = np.zeros(shape, np.uint8)
		for x0, y0, x1, y1 in regions:
			mask[max(0, y0) : min(height, y1), max(0, x0) : min(width, x1)] = 255
	else:
		mask = np.full(shape, 255, np.uint8)
	mask[:40, :] = 0
	mask[-40:, -160:] = 0
	return mask


def extract_features(image_bgr: np.ndarray, regions: Sequence[Rect] | None = None) -> Features:
	gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
	gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
	orb = cv2.ORB_create(MAX_FEATURES, fastThreshold=FAST_THRESHOLD)
	keypoints, descriptors = orb.detectAndCompute(gray, feature_mask(gray.shape, regions))
	return Features(tuple(keypoints), descriptors)


def align(before: Features, after: Features) -> Alignment:
	"""Estimate how `after` is shifted and rotated relative to `before`."""
	if before.descriptors is None or after.descriptors is None:
		return Alignment(inliers=0)
	matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
	matches = sorted(matcher.match(before.descriptors, after.descriptors), key=lambda m: m.distance)[:MAX_MATCHES]
	if len(matches) < 3:
		return Alignment(inliers=0)
	points_before = np.float32([before.keypoints[m.queryIdx].pt for m in matches])
	points_after = np.float32([after.keypoints[m.trainIdx].pt for m in matches])
	transform, inlier_mask = cv2.estimateAffinePartial2D(
		points_before, points_after, method=cv2.RANSAC, ransacReprojThreshold=RANSAC_THRESHOLD_PX
	)
	if transform is None:
		return Alignment(inliers=0)
	return Alignment(
		inliers=int(inlier_mask.sum()),
		shift_px=float(np.hypot(transform[0, 2], transform[1, 2])),
		rotation_deg=float(np.degrees(np.arctan2(transform[1, 0], transform[0, 0]))),
	)
