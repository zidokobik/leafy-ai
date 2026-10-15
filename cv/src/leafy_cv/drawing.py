"""Small drawing helpers shared by the overlays, check images and labelling tools."""

import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_SIMPLEX
WHITE, BLACK = (255, 255, 255), (0, 0, 0)
# One colour per row of holes (BGR), repeated after six rows: the check overlays and the click tool.
ROW_PALETTE = [(66, 135, 245), (245, 170, 66), (80, 200, 120), (200, 90, 220), (240, 220, 70), (90, 220, 230)]


def put_outlined_text(
	image: np.ndarray, text: str, at: tuple[int, int], scale: float, outline: int = 3, colour=WHITE
) -> None:
	"""Text that stays readable on any background: a thick black copy under a thin coloured one (in place)."""
	cv2.putText(image, text, at, FONT, scale, BLACK, outline)
	cv2.putText(image, text, at, FONT, scale, colour, 1)


def draw_plant_outline(image_bgr: np.ndarray, plant_mask: np.ndarray, colour=WHITE) -> np.ndarray:
	"""Thin contour of the plant pixels on a copy of the image."""
	out = image_bgr.copy()
	contours, _ = cv2.findContours(plant_mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
	cv2.drawContours(out, contours, -1, colour, 1)
	return out


def dim_outside(image_bgr: np.ndarray, mask: np.ndarray, factor: float = 0.35) -> np.ndarray:
	"""A copy of the image with everything outside the mask darkened (the outline stands out)."""
	out = image_bgr.copy()
	out[~mask] = (out[~mask] * factor).astype(np.uint8)
	return out
