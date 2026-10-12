"""tools/build_frame_index.py must not overwrite the frame index by accident (it was corrected by hand on 11 Oct)."""

import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "build_frame_index.py"


def run_main(monkeypatch, *argv):
	spec = importlib.util.spec_from_file_location("build_frame_index", TOOL)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	monkeypatch.setattr(sys, "argv", ["build_frame_index.py", *argv])
	module.main()


def test_refuses_to_overwrite_an_existing_index(tmp_path, monkeypatch):
	(tmp_path / "frame_index.csv").write_text("hand-corrected\n")
	with pytest.raises(SystemExit, match="--overwrite"):
		run_main(monkeypatch, "--frames-root", str(tmp_path / "frames"), "--out-dir", str(tmp_path))
	assert (tmp_path / "frame_index.csv").read_text() == "hand-corrected\n"


def test_overwrite_flag_lets_it_continue(tmp_path, monkeypatch):
	(tmp_path / "frames").mkdir()
	(tmp_path / "periods.csv").write_text("hand-corrected\n")
	with pytest.raises(SystemExit, match="No frames found"):  # got past the guard; nothing to index here
		run_main(monkeypatch, "--frames-root", str(tmp_path / "frames"), "--out-dir", str(tmp_path), "--overwrite")
	assert (tmp_path / "periods.csv").read_text() == "hand-corrected\n"
