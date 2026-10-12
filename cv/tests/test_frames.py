from datetime import datetime
from pathlib import Path

from leafy_cv.frames import list_frames, parse_frame_path


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
