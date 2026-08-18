# Leafy Project Guide

## Project Structure

This repository contains the complete Leafy application:

- `main.py` is the FastAPI application entry point. It creates the app, registers the backend routers, and serves the built frontend in production.
- `backend/` contains the Python service layer and business logic. `backend/settings.py` contains application settings, and `backend/router/` contains the API routers.
- `frontend/` contains the React and TypeScript dashboard. Its source is organized under `frontend/src/`, with API code, shared components, and feature-specific UI grouped by responsibility.
- `sample-data/` contains local sample camera and sensor data.

The frontend was previously maintained as a separate repository and is now part of this repository. Its existing organization is not completely uniform; follow the current feature-oriented structure for new work and avoid unrelated cleanup.

## Framework

- Runtime: Python 3.14+
- Web framework: FastAPI
- ASGI server: Uvicorn
- Data validation/models: Pydantic v2
- Frontend: React, TypeScript, and Vite

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

The Python project uses `ruff` for code formatting and linting. Configuration is defined in the `[tool.ruff]` section and any `[tool.ruff.<subsection>]` of `pyproject.toml`.

The frontend uses the existing ESLint and TypeScript configuration in `frontend/`. Follow the conventions in `frontend/AGENTS.md` for frontend changes.

Format the codebase:

```bash
uv run ruff format .
```

Optional lint check:

```bash
uv run ruff check .
```

## Local Development

Install frontend dependencies from the frontend directory:

```bash
cd frontend
npm install
```

Start the API in reload mode from the repository root:

```bash
uv run uvicorn main:app --reload
```

Suggested explicit host/port when needed:

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Start the Vite development server in a separate terminal:

```bash
cd frontend
npm run dev
```

The API is mounted under `/api`. Vite proxies development requests from `/api` to the FastAPI server.

## Validation

For backend changes, run:

```bash
uv run ruff format .
uv run ruff check .
```

For frontend changes, run from `frontend/`:

```bash
npm run lint
npm run build
```
