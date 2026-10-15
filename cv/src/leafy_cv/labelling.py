"""The labelling session shared by tools/label_holes.py and tools/label_masks.py.

One item at a time; the answer is saved after every key (so labelling can stop and resume at any time); b goes
back one answer, also into answers given in an earlier session; q or Esc quits. The screen is the same for both
tools: a close-up on the left, the same close-up untouched on the right, the whole frame below with the close-up
marked, and the instructions beside it.
"""

import csv
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path

import cv2
import numpy as np

from leafy_cv.csv_files import write_csv

THUMB_WIDTH = 352  # px: the whole frame, small, below the close-ups
GAP = 8
TEXT_COLOUR = (235, 235, 235)
BACK, QUIT, ESC = ord("b"), ord("q"), 27


class ReadinessLabel(StrEnum):
	"""Answers in labels/readiness/labels.csv (tools/label_holes.py)."""

	CROWDED = "crowded"
	NOT_CROWDED = "not_crowded"
	EMPTY = "empty"
	UNSURE = "unsure"


class PlantLabel(StrEnum):
	"""Answers in labels/plant_masks/labels.csv (tools/label_masks.py)."""

	PLANT = "plant"
	NOT_PLANT = "not_plant"
	MIXED = "mixed"
	SKIP = "skip"


def read_labels(path: Path) -> list[dict[str, str]]:
	if not path.exists():
		return []
	with open(path, encoding="utf-8") as handle:
		return list(csv.DictReader(handle))


@dataclass
class LabelSession:
	"""The items still to label, in order, and the answers so far (one labels.csv row each)."""

	items: list[dict]  # every item, in labelling order
	id_field: str  # the column that names an item, e.g. item_id
	labels: list[dict]  # the answers so far, oldest first
	queue: list[dict] = field(init=False)  # items without an answer when the session started (+ items taken back)
	position: int = 0  # the item on screen is queue[position]

	def __post_init__(self) -> None:
		done = {row[self.id_field] for row in self.labels}
		self.queue = [item for item in self.items if item[self.id_field] not in done]

	@property
	def current(self) -> dict | None:
		return self.queue[self.position] if self.position < len(self.queue) else None

	def answer(self, label: str, labelled_at: str) -> None:
		self.labels.append({self.id_field: self.current[self.id_field], "label": label, "labelled_at": labelled_at})
		self.position += 1

	def back(self) -> None:
		"""Take back the last answer and show its item again."""
		if not self.labels:
			return
		undone = self.labels.pop()
		if self.position > 0 and self.queue[self.position - 1][self.id_field] == undone[self.id_field]:
			self.position -= 1
			return
		# answered in an earlier session: put it back in front (if it is still one of the items)
		item = next((i for i in self.items if i[self.id_field] == undone[self.id_field]), None)
		if item is not None:
			self.queue.insert(self.position, item)

	def count(self, label: str) -> int:
		return sum(row["label"] == label for row in self.labels)


def run_session(
	session: LabelSession,
	labels_path: Path,
	answer_keys: dict[int, str],
	screen: Callable[[dict], np.ndarray],
	window: str,
) -> None:
	"""Show items until all are answered, the user quits or the window is closed. Answers are saved after every
	key, through a temporary file, so stopping at any moment loses nothing."""
	fields = [session.id_field, "label", "labelled_at"]
	cv2.namedWindow(window, cv2.WINDOW_AUTOSIZE)
	while session.current is not None:
		cv2.imshow(window, screen(session.current))
		key = cv2.waitKey(0) & 0xFF
		if key in answer_keys:
			session.answer(answer_keys[key], datetime.now().astimezone().isoformat(timespec="seconds"))
			write_csv(labels_path, fields, session.labels)
		elif key == BACK and session.labels:
			session.back()
			write_csv(labels_path, fields, session.labels)
		elif key in (QUIT, ESC):
			break
		if cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
			break
	cv2.destroyAllWindows()


def thumbnail(marked: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
	"""The whole frame, THUMB_WIDTH wide, with the close-up's box drawn on it (draws on `marked`: pass a copy)."""
	x0, y0, x1, y1 = box
	cv2.rectangle(marked, (x0, y0), (x1, y1), (255, 255, 255), 2)
	height, width = marked.shape[:2]
	return cv2.resize(marked, (THUMB_WIDTH, int(height * THUMB_WIDTH / width)))


def compose(
	left: np.ndarray, right: np.ndarray, thumb: np.ndarray, lines: list[str], top_height: int, width: int
) -> np.ndarray:
	"""The labelling screen: the two close-ups on top (top_height high), the thumbnail below, the text beside it."""
	canvas = np.full((top_height + GAP + thumb.shape[0] + 8, width, 3), 32, np.uint8)
	canvas[: left.shape[0], : left.shape[1]] = left
	canvas[: right.shape[0], left.shape[1] + GAP : left.shape[1] + GAP + right.shape[1]] = right
	ty = top_height + GAP
	canvas[ty : ty + thumb.shape[0], :THUMB_WIDTH] = thumb
	for i, line in enumerate(lines):
		cv2.putText(canvas, line, (THUMB_WIDTH + 14, ty + 22 + 22 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.5, TEXT_COLOUR, 1)
	return canvas
