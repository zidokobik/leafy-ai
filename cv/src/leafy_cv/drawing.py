"""Small drawing helpers shared by the overlays, check images and labelling tools."""

import cv2
import numpy as np

FONT = cv2.FONT_HERSHEY_SIMPLEX
WHITE, BLACK = (255, 255, 255), (0, 0, 0)


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
