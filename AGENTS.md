# Backend Project Guide

## Framework

- Runtime: Python 3.14+
- Web framework: FastAPI
- ASGI server: Uvicorn
- Data validation/models: Pydantic v2

## uv Workflow

This project should be managed with `uv`, which is a tool for managing Python virtual environments and dependencies.

Install/sync dependencies:

```bash
uv sync
```

Add a dependency:

```bash
uv add <package>
```

Run project commands inside the managed environment:

```bash
uv run <command>
```

## Formatting and Style

This project uses `ruff` for code formatting and linting.
Configuration is defined in the `[tool.ruff]` section and any `[tool.ruff.<subsection>]` of `pyproject.toml`.

Format the codebase:

```bash
uv run ruff format .
```

Optional lint check:

```bash
uv run ruff check .
```

## Local Development

Start the API in reload mode:

```bash
uv run uvicorn main:app --reload
```

Suggested explicit host/port when needed:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
