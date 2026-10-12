"""Download the MobileSAM weights (40 MB, Apache-2.0) into cv/models/ and check them.

Usage (from the cv/ folder):
	uv run python tools/download_weights.py

models/ is ignored by git. Running this again does nothing if the file is already correct.
"""

import hashlib
import urllib.request
from pathlib import Path

from leafy_cv.segment import DEFAULT_WEIGHTS, WEIGHTS_SHA256, WEIGHTS_URL


def sha256(path: Path) -> str:
	digest = hashlib.sha256()
	with open(path, "rb") as handle:
		for chunk in iter(lambda: handle.read(1 << 20), b""):
			digest.update(chunk)
	return digest.hexdigest()


def main() -> None:
	target = DEFAULT_WEIGHTS
	if target.exists() and sha256(target) == WEIGHTS_SHA256:
		print(f"Already there and correct: {target}")
		return
	target.parent.mkdir(parents=True, exist_ok=True)
	partial = target.with_suffix(".part")
	print(f"Downloading {WEIGHTS_URL} ...")
	urllib.request.urlretrieve(WEIGHTS_URL, partial)
	if sha256(partial) != WEIGHTS_SHA256:
		partial.unlink()
		raise SystemExit("Downloaded file doesn't match the expected checksum; not saved. Try again.")
	partial.replace(target)
	print(f"Saved and checked: {target}")


if __name__ == "__main__":
	main()
