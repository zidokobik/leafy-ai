# Leafy Project Guide

## Project Structure

This repository contains the complete Leafy application:

- `main.py` is the FastAPI application entry point. It creates the app, registers the backend routers, and serves the built frontend in production.
- `backend/` contains the Python service layer and business logic. `backend/settings.py` contains application settings, `backend/router/` contains the API routers, `backend/schemas/` the request and response models, and `backend/services/` the reusable logic.
- Keep routers thin. Put the actual work in `backend/services/`, where functions take an `AsyncSession` plus plain arguments rather than FastAPI dependencies, so the planned chat agent can call them as tools without going through HTTP.
- `frontend/` contains the React and TypeScript dashboard. Its source is organized under `frontend/src/`, with API code, shared shell components, shadcn/ui primitives, and feature-specific UI grouped by responsibility.
- `sample-data/` contains the static camera image served by the mock camera route.

The frontend uses client-side routing with one page per sidebar entry: Overview, Agents, Schedules and Devices. Overview charts sensor history for a selected `before` to `end` interval using Recharts via shadcn chart components; Agents provides the interactive agent chat; and Schedules manages recurring agent instructions. Devices is a placeholder. Adding a page means creating a feature folder, registering the route in `frontend/src/App.tsx`, and adding the entry to `frontend/src/components/navigation.ts`. Follow the conventions in `frontend/AGENTS.md` for frontend changes.

## Database Schema

- See `schema.sql` for the database schema and table definitions. Use it only for context, it is not expected to be run directly.

## Framework

- Runtime: Python 3.14+
- Web framework: FastAPI
- ASGI server: Uvicorn
- Data validation/models: Pydantic v2
- Frontend: React, TypeScript, Vite, Tailwind CSS v4, and shadcn/ui, with `react-router-dom` for routing and `recharts` for charts

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
