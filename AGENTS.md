# Leafy Project Guide

## Project Structure

This repository contains the complete Leafy application:

- `main.py` is the FastAPI application entry point. It creates the app, registers the backend routers, and serves the built frontend in production.
- `backend/` contains the Python service layer and business logic. `backend/settings.py` contains application settings, and `backend/router/` contains the API routers.
- `frontend/` contains the React and TypeScript dashboard. Its source is organized under `frontend/src/`, with API code, shared components, and feature-specific UI grouped by responsibility.
- `sample-data/` contains local sample camera and sensor data.

The frontend was previously maintained as a separate repository and is now part of this repository. Its existing organization is not completely uniform; follow the current feature-oriented structure for new work and avoid unrelated cleanup.

## Database Schema

- `schema.sql` is the source of truth for the current Postgres schema, including defaults, primary keys, and foreign-key constraints. Read it before adding or changing database models, queries, migrations, or API contracts that persist data.
- Database access is asynchronous through SQLAlchemy/SQLModel and `asyncpg`; use the existing database session dependency and model conventions in `backend/`.
- The schema is organized into these domains:
	- Identity and authorization: `users`, `roles`, `permissions`, `user_role`, and `role_permission`.
	- Monitoring: `sensor_data`, `devices`, `device_limits`, `levels`, and `cameras`.
	- Crop operations: `crop_cycles`, `growth_stages`, `grow_schedules`, and `schedule_targets`.
	- Vision and automation: `images`, `ai_decisions`, `decision_evidence`, `approvals`, and `command_executions`.
	- Notifications and auditability: `alerts` and `audit_log`.
- Follow the explicit foreign keys in `schema.sql`: devices and cameras belong to levels; crop cycles belong to levels and reference growth stages; grow schedules belong to crop cycles; schedule targets reference schedules and growth stages; AI decisions reference crop cycles, schedules, and devices; decision evidence references decisions, sensor readings, and images; approvals reference decisions and users; command executions reference decisions, devices, and users; alerts reference devices, decisions, crop cycles, and users; audit records reference users.
- Do not infer a foreign-key relationship from a similarly named column. For example, `images.crop_cycle_id`, `images.experiment_id`, and `audit_log.entity_id` are not declared foreign keys in `schema.sql`.
- Preserve database ID types when creating models or schemas: UUIDs are used for users, permissions, sensor readings, levels, and devices; identity `int8` values are used by most operational, decision, alert, and audit tables. Do not convert IDs to strings or integers merely for frontend convenience.
- Nullable columns are intentional. Keep optional fields optional in Pydantic schemas and handle missing measurements, targets, relationships, and status values explicitly.
- `sensor_data` is time-series-like monitoring data keyed by `created_at`; `images` are camera captures keyed by `captured_at`. Keep timestamps timezone-aware and use the database timestamps rather than client-generated event times when recording persisted events.
- Treat join tables (`user_role` and `role_permission`) and evidence tables as relationships, not duplicated domain records. Preserve their composite key behavior when querying or writing them.

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
