from leafy_cv.csv_files import format_optional, write_csv


def test_write_csv_writes_header_and_rows_and_leaves_no_temporary_file(tmp_path):
	path = tmp_path / "out.csv"
	write_csv(path, ["a", "b"], [{"a": 1, "b": "x"}, {"a": 2, "b": ""}])
	assert path.read_text(encoding="utf-8").splitlines() == ["a,b", "1,x", "2,"]
	assert list(tmp_path.iterdir()) == [path]


def test_write_csv_with_no_rows_writes_the_header(tmp_path):
	write_csv(tmp_path / "out.csv", ["a", "b"], [])
	assert (tmp_path / "out.csv").read_text(encoding="utf-8").splitlines() == ["a,b"]


def test_format_optional():
	assert format_optional(None, ".2f") == ""
	assert format_optional(0.12345, ".2f") == "0.12"
	assert format_optional(7) == "7"
