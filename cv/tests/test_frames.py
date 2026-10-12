from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import pytest

from leafy_cv.frames import list_frames, parse_frame_path, read_image


def test_parses_camera_and_time_from_file_name():
	frame = parse_frame_path(Path("level1_camera2/level1_camera2_20260922_130030.jpg"))
	assert frame is not None
	assert frame.camera_id == "level1_camera2"
	assert frame.captured_at == datetime(2026, 9, 22, 13, 0, 30)


def test_rejects_names_that_do_not_match():
	assert parse_frame_path(Path("level1_camera2/photo.jpg")) is None
	assert parse_frame_path(Path("level1_camera2/level1_camera2_20260922.jpg")) is None


def test_lists_frames_sorted_and_skips_misfiled(tmp_path):
	camera = tmp_path / "level1_camera1"
	camera.mkdir()
	for name in ["level1_camera1_20260916_050025.jpg", "level1_camera1_20260915_100024.jpg", "notes.jpg"]:
		(camera / name).write_bytes(b"")
	(tmp_path / "other").mkdir()
	(tmp_path / "other" / "level1_camera1_20260915_110000.jpg").write_bytes(b"")  # wrong folder

	by_camera, skipped = list_frames(tmp_path)

	assert [f.path.name for f in by_camera["level1_camera1"]] == [
		"level1_camera1_20260915_100024.jpg",
		"level1_camera1_20260916_050025.jpg",
	]
	assert len(skipped) == 2


def test_read_image_returns_the_pixels(tmp_path):
	image = np.zeros((4, 6, 3), np.uint8)
	image[1, 2] = (10, 20, 30)
	cv2.imwrite(str(tmp_path / "a.png"), image)
	assert (read_image(tmp_path / "a.png") == image).all()


def test_read_image_says_which_file_is_missing_or_corrupt(tmp_path):
	(tmp_path / "empty.jpg").write_bytes(b"")
	for path in (tmp_path / "missing.jpg", tmp_path / "empty.jpg"):
		with pytest.raises(FileNotFoundError, match=path.name):
			read_image(path)
