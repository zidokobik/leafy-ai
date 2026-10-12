"""Keep the repo-root `uv run pytest` (backend environment, no leafy_cv installed) from collecting cv tests.

Inside cv/ (`uv run pytest` after `uv sync`) leafy_cv is installed, so the tests run as normal.
"""

import importlib.util

if importlib.util.find_spec("leafy_cv") is None:
	collect_ignore_glob = ["*"]
