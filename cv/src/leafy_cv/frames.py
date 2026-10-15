"""Find camera frames on disk and read the camera ID and capture time from each file name.

Expected layout: <frames_root>/<camera_id>/<camera_id>_<YYYYMMDD>_<HHMMSS>.jpg
for example E:\\Claude\\level1_camera2\\level1_camera2_20260922_130030.jpg
"""

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# Overlays burnt into every frame: a timestamp strip along the top and a watermark in the bottom-right corner.
TIMESTAMP_STRIP_PX = 40
WATERMARK_PX = (160, 40)  # width, height
FILENAME_PATTERN = re.compile(r"^(?P<camera>level\d+_camera\d+)_(?P<date>\d{8})_(?P<time>\d{6})\.jpg$")


@dataclass(frozen=True)
class Frame:
	camera_id: str
	captured_at: datetime  # as written in the file name; the timezone is not confirmed yet
	path: Path


def parse_frame_path(path: Path) -> Frame | None:
	"""Return a Frame, or None when the file name doesn't follow <camera>_<YYYYMMDD>_<HHMMSS>.jpg."""
	match = FILENAME_PATTERN.match(path.name)
	if match is None:
		return None
	captured_at = datetime.strptime(match["date"] + match["time"], "%Y%m%d%H%M%S")
	return Frame(camera_id=match["camera"], captured_at=captured_at, path=path)


def list_frames(frames_root: Path) -> tuple[dict[str, list[Frame]], list[Path]]:
	"""All frames under frames_root/<camera_id>/, grouped by camera and sorted by time.

	Also returns the .jpg files that were skipped because their name or folder didn't match.
	"""
	by_camera: dict[str, list[Frame]] = {}
	skipped: list[Path] = []
	for path in sorted(frames_root.glob("*/*.jpg")):
		frame = parse_frame_path(path)
		if frame is None or frame.camera_id != path.parent.name:
			skipped.append(path)
			continue
		by_camera.setdefault(frame.camera_id, []).append(frame)
	for frames in by_camera.values():
		frames.sort(key=lambda frame: frame.captured_at)
	return by_camera, skipped


def read_image(path: Path) -> np.ndarray:
	"""The image at path (BGR). cv2.imread returns None for a missing or unreadable file; this says so instead of
	failing later with an unrelated error."""
	image = cv2.imread(str(path))
	if image is None:
		raise FileNotFoundError(f"Could not read the image {path} (missing or corrupt)")
	return image
