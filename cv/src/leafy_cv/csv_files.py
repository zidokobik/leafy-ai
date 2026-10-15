"""Writing and reading the CSV outputs. Every CSV is written through write_csv, so an interrupted write never leaves a
half-written file."""

import csv
from collections.abc import Iterator, Sequence
from pathlib import Path


def write_csv(path: Path, fields: Sequence[str], rows: Sequence[dict], extrasaction: str = "raise") -> None:
	"""Header + rows, written to a temporary file first and then moved into place, so an interrupted write never
	leaves a half-written file. `extrasaction="ignore"` drops keys that aren't in `fields`."""
	tmp = path.with_suffix(".tmp")
	with open(tmp, "w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction=extrasaction)
		writer.writeheader()
		writer.writerows(rows)
	tmp.replace(path)


def format_optional(value: float | None, spec: str = "") -> str:
	"""A value for a CSV cell: "" when missing, else formatted with `spec` (e.g. ".4f")."""
	return "" if value is None else format(value, spec)


def read_observations(runs_dir: Path) -> Iterator[dict[str, str]]:
	"""Every row of every map's observations.csv under runs_dir (data/runs/<camera>_<period>/), map by map."""
	for path in sorted(runs_dir.glob("*/observations.csv")):
		with open(path, encoding="utf-8") as handle:
			yield from csv.DictReader(handle)
