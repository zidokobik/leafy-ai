"""Segment plants with MobileSAM, prompted at points (usually hole centres).

MobileSAM is asked "what object is at this point?" and returns three candidate outlines
(roughly: a small part, a bigger part, the whole object) with a predicted quality score each.

Neighbouring hole centres can be passed as "negative" points. They tell the model "not this",
which stops one plant's outline swallowing the plant next to it. Leaves that reach into a
neighbour's cell are still allowed: only the neighbour's centre is excluded.

torch and mobile_sam are imported only when a Segmenter is created, so the rest of leafy_cv
works without them.
"""

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

DEFAULT_WEIGHTS = Path(__file__).resolve().parents[2] / "models" / "mobile_sam.pt"
WEIGHTS_URL = "https://raw.githubusercontent.com/ChaoningZhang/MobileSAM/master/weights/mobile_sam.pt"
WEIGHTS_SHA256 = "6dbb90523a35330fedd7f1d3dfc66f995213d81b29a5ca8108dbcdd4e37d6c2f"
PAD_LABEL = -1  # SAM ignores points with this label; used to give every prompt the same length
# Prompts sent to the mask decoder at once. Its output is 3 full-size float masks per prompt (~5 MB each),
# so 290 prompts at once (camera 1's zone grid) used 6 GB and was killed (7 Oct); 32 keeps it under 0.6 GB.
PROMPT_BATCH = 32


@dataclass(frozen=True)
class PointMasks:
	"""MobileSAM's three candidate outlines for one prompt point."""

	point: tuple[float, float]
	masks: np.ndarray  # (3, height, width) bool
	scores: np.ndarray  # (3,) predicted quality (IoU) of each candidate

	@property
	def best(self) -> int:
		"""Index of the candidate the model rates highest."""
		return int(np.argmax(self.scores))


def build_prompts(points: np.ndarray, negatives: list[list[int]] | None = None) -> tuple[np.ndarray, np.ndarray]:
	"""Point coordinates (B, N, 2) and labels (B, N) for B prompts.

	Prompt i is points[i] as positive (label 1) plus points[j] for j in negatives[i] as negative
	(label 0). Shorter prompts are padded with label -1 so all have the same length N.
	"""
	points = np.asarray(points, dtype=np.float32).reshape(-1, 2)
	negatives = negatives or [[] for _ in range(len(points))]
	if len(negatives) != len(points):
		raise ValueError("negatives needs one list per point")
	width = 1 + max((len(n) for n in negatives), default=0)
	coords = np.zeros((len(points), width, 2), np.float32)
	labels = np.full((len(points), width), PAD_LABEL, np.float32)
	for i, point in enumerate(points):
		coords[i, 0], labels[i, 0] = point, 1
		for k, j in enumerate(negatives[i], start=1):
			coords[i, k], labels[i, k] = points[j], 0
	return coords, labels


def file_sha256(path: Path) -> str:
	"""SHA-256 of a file, read in 1 MB chunks."""
	digest = hashlib.sha256()
	with open(path, "rb") as handle:
		for chunk in iter(lambda: handle.read(1 << 20), b""):
			digest.update(chunk)
	return digest.hexdigest()


class Segmenter:
	"""MobileSAM on CPU. Call set_image once per frame, then predict for any number of points."""

	def __init__(self, weights: Path = DEFAULT_WEIGHTS, threads: int | None = None):
		weights = Path(weights)
		if not weights.exists():
			raise FileNotFoundError(f"{weights} not found: run `uv run python tools/download_weights.py` first")
		# the file is unpickled by torch.load, so only the known file is loaded (older torch versions would run code
		# from a replaced file)
		if file_sha256(weights) != WEIGHTS_SHA256:
			raise ValueError(
				f"{weights} is not the expected MobileSAM file: run `uv run python tools/download_weights.py`"
			)
		with warnings.catch_warnings():
			warnings.simplefilter("ignore")  # timm deprecation notices from inside mobile_sam
			import torch
			from mobile_sam import SamPredictor, sam_model_registry

			if threads:
				torch.set_num_threads(threads)
			model = sam_model_registry["vit_t"](checkpoint=str(weights))
		model.eval()
		self._torch = torch
		self._predictor = SamPredictor(model)
		self._image_size: tuple[int, int] | None = None

	def set_image(self, image_bgr: np.ndarray) -> None:
		"""Run the image encoder (the slow part: a few seconds on a laptop CPU)."""
		with self._torch.inference_mode():
			self._predictor.set_image(cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB))
		self._image_size = image_bgr.shape[:2]

	def predict(self, points: np.ndarray, negatives: list[list[int]] | None = None) -> list[PointMasks]:
		"""Three candidate masks per point. See build_prompts for `negatives`."""
		if self._image_size is None:
			raise RuntimeError("call set_image first")
		points = np.asarray(points, dtype=np.float32).reshape(-1, 2)
		if len(points) == 0:
			return []
		coords, labels = build_prompts(points, negatives)
		torch = self._torch
		out = []
		for start in range(0, len(points), PROMPT_BATCH):
			stop = start + PROMPT_BATCH
			with torch.inference_mode():
				coords_t = self._predictor.transform.apply_coords_torch(
					torch.from_numpy(coords[start:stop]), self._image_size
				)
				masks, scores, _ = self._predictor.predict_torch(
					coords_t, torch.from_numpy(labels[start:stop]), multimask_output=True
				)
			masks, scores = masks.numpy(), scores.numpy()
			out += [
				PointMasks(point=(float(p[0]), float(p[1])), masks=masks[k], scores=scores[k])
				for k, p in enumerate(points[start:stop])
			]
		return out
