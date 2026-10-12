"""Decide whether a MobileSAM outline is plant or not (board, pot, hole, wall, glare).

The decision uses only what the outlined pixels look like: colour and texture. It never uses
the outline's size or shape, because a closed canopy is one huge plant region and must not be
thrown away for being big (that's how a quick size-based prototype failed).

Training (tools/train_plant_filter.py) fits a logistic regression on hand labels. The result
is stored as plain JSON (feature names, scaling, weights), so using it needs only numpy.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

FEATURE_NAMES = (
	"hue_cos",  # hue as a point on a circle, so red at 0 and 180 degrees count as close
	"hue_sin",
	"sat_mean",
	"sat_std",
	"val_mean",
	"val_std",
	"lab_l_mean",
	"lab_a_mean",  # green (-) to magenta (+)
	"lab_b_mean",  # blue (-) to yellow (+)
	"lab_a_std",
	"lab_b_std",
	"exg_mean",  # excess green 2g - r - b on brightness-normalised colour
	"exg_std",
	"gray_std",  # texture: leaves are veined and shaded, board and walls are flat
	"grad_mean",
	"lap_mean",
)
MIN_MASK_PIXELS = 20


@dataclass(frozen=True)
class ImageLayers:
	"""Whole-image conversions that mask_features needs. Compute once per frame when scoring many outlines."""

	hsv: np.ndarray
	lab: np.ndarray
	gray: np.ndarray
	grad: np.ndarray
	lap: np.ndarray

	@classmethod
	def of(cls, image_bgr: np.ndarray) -> "ImageLayers":
		gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
		return cls(
			hsv=cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV),
			lab=cv2.cvtColor(image_bgr, cv2.COLOR_BGR2LAB),
			gray=gray,
			grad=cv2.magnitude(cv2.Sobel(gray, cv2.CV_32F, 1, 0), cv2.Sobel(gray, cv2.CV_32F, 0, 1)),
			lap=np.abs(cv2.Laplacian(gray, cv2.CV_32F)),
		)


def mask_features(image_bgr: np.ndarray, mask: np.ndarray, layers: ImageLayers | None = None) -> np.ndarray:
	"""Colour and texture of the pixels inside `mask`. Independent of the mask's size.

	`layers` (ImageLayers.of(image_bgr)) only saves time; the result is identical without it.
	"""
	mask = mask.astype(bool)
	if mask.sum() < MIN_MASK_PIXELS:
		raise ValueError(f"mask has fewer than {MIN_MASK_PIXELS} pixels")
	layers = layers or ImageLayers.of(image_bgr)
	hsv = layers.hsv[mask].astype(np.float32)
	lab = layers.lab[mask].astype(np.float32)
	bgr = image_bgr[mask].astype(np.float32)
	angle = np.deg2rad(hsv[:, 0] * 2.0)  # OpenCV hue is 0-180
	weight = hsv[:, 1] / 255.0  # grey pixels have no meaningful hue
	total = max(float(weight.sum()), 1e-6)
	chroma = bgr / np.maximum(bgr.sum(axis=1, keepdims=True), 1.0)
	exg = 2 * chroma[:, 1] - chroma[:, 2] - chroma[:, 0]

	gray, grad, lap = layers.gray, layers.grad, layers.lap
	# texture inside the region only: shrink the mask so its own outline doesn't count as texture
	inner = cv2.erode(mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
	if inner.sum() < MIN_MASK_PIXELS:
		inner = mask

	return np.array(
		[
			float((np.cos(angle) * weight).sum() / total),
			float((np.sin(angle) * weight).sum() / total),
			hsv[:, 1].mean() / 255,
			hsv[:, 1].std() / 255,
			hsv[:, 2].mean() / 255,
			hsv[:, 2].std() / 255,
			lab[:, 0].mean() / 255,
			(lab[:, 1].mean() - 128) / 128,
			(lab[:, 2].mean() - 128) / 128,
			lab[:, 1].std() / 128,
			lab[:, 2].std() / 128,
			exg.mean(),
			exg.std(),
			gray[mask].std() / 255,
			grad[inner].mean() / 255,
			lap[inner].mean() / 255,
		],
		dtype=np.float64,
	)


@dataclass(frozen=True)
class PlantFilter:
	"""A trained logistic regression: P(plant) from mask_features."""

	feature_names: tuple[str, ...]
	mean: np.ndarray
	scale: np.ndarray
	weights: np.ndarray
	bias: float
	threshold: float = 0.5
	notes: str = ""

	def probability(self, features: np.ndarray) -> np.ndarray:
		"""P(plant) for one feature vector or a (n, features) array."""
		z = (np.atleast_2d(features) - self.mean) / self.scale @ self.weights + self.bias
		return 1.0 / (1.0 + np.exp(-z))

	def is_plant(self, features: np.ndarray) -> np.ndarray:
		return self.probability(features) >= self.threshold

	def save(self, path: Path) -> None:
		path.parent.mkdir(parents=True, exist_ok=True)
		data = {
			"feature_names": list(self.feature_names),
			"mean": self.mean.tolist(),
			"scale": self.scale.tolist(),
			"weights": self.weights.tolist(),
			"bias": self.bias,
			"threshold": self.threshold,
			"notes": self.notes,
		}
		path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

	@classmethod
	def load(cls, path: Path) -> "PlantFilter":
		data = json.loads(Path(path).read_text(encoding="utf-8"))
		if tuple(data["feature_names"]) != FEATURE_NAMES:
			raise ValueError(f"{path} was trained on different features; retrain it")
		return cls(
			feature_names=tuple(data["feature_names"]),
			mean=np.array(data["mean"]),
			scale=np.array(data["scale"]),
			weights=np.array(data["weights"]),
			bias=float(data["bias"]),
			threshold=float(data["threshold"]),
			notes=data.get("notes", ""),
		)


def pack_masks(masks: np.ndarray) -> np.ndarray:
	"""(n, height, width) bool -> compact uint8 bits for storage."""
	return np.packbits(masks.astype(bool), axis=-1)


def unpack_masks(packed: np.ndarray, width: int) -> np.ndarray:
	return np.unpackbits(packed, axis=-1, count=width).astype(bool)
