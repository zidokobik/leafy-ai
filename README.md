# Leafy

Leafy is a monitoring and control application for a hydroponic farm. A React dashboard and an AI agent sit on top of a FastAPI backend that collects sensor data, syncs camera images, manages alerts and email notifications, and controls the farm's TP-Link Kasa powerboards — with a person approving every device run the agent proposes.

## Features

- **Sensor monitoring** — the backend polls the farm's ThingSpeak feed every 30 seconds and stores water pH, EC, water/ambient temperature, humidity and reservoir level in Postgres. Overview charts any time interval, with 24-hour/7-day/30-day presets or a custom range.
- **Cameras** — an hourly job copies the latest image for every camera from the AWS API (which only hands out short-lived presigned links) into a public Supabase Storage bucket, and Overview shows the resulting camera grid.
- **AI agent** — chat on the Agents page or in the floating "Ask agent" sheet on Overview. The agent reads sensors and camera images, raises/updates/resolves alerts, sends admin emails, and proposes device runs. Conversations are persisted, and the Schedules page manages recurring agent runs (cron expressions) whose transcripts are browsable read-only.
- **Proposal-based device control** — the agent can only *propose* switching a device on for a set duration (at most 24 hours); a person approves or rejects each proposal on Overview or Logs. Approving switches the Kasa outlet on and arms an auto-off timer; timers are re-armed on startup, and a failed switch-off raises a critical alert. People can also switch devices on and off directly on the Devices page.
- **Alerts** — stateful dashboard alerts with an explicit lifecycle: dismissing an alert only hides it from the Overview pin, resolving is a separate action, and re-raising an active alert key updates it in place instead of stacking duplicates.
- **Email notifications** — admin recipients and a log of every send, managed on the Alerts page. SMTP credentials live in `.env`, and the agent is prompt-guided to email only critical escalations and explicitly requested reports.

## Project Structure

Leafy is organized as one application with a Python service layer and a React user interface. The two layers are developed separately, but they live in this repository and communicate through the FastAPI API.

```text
.
├── main.py                 # FastAPI application entry point
├── system_prompt.md        # The AI agent's system prompt
├── schema.sql              # Database schema, for reference only (not meant to be executed)
├── backend/                # Python code and business logic
│   ├── settings.py         # Application settings, loaded from .env
│   ├── cli.py              # Typer CLI: user management and on-demand camera sync
│   ├── db_models/*         # SQLModel tables
│   ├── dependencies/*      # FastAPI dependencies (auth, database session)
│   ├── router/*            # API routers, mounted under /api/v1
│   ├── schemas/*           # Request and response models
│   ├── services/*          # Reusable business logic; services/agent/ is the agent and its tools
│   └── schedule/*          # APScheduler jobs: sensor polling, camera sync, scheduled agent runs
├── frontend/               # React + TypeScript dashboard
│   ├── components.json     # shadcn/ui configuration
│   ├── vite.config.ts      # Vite, React, Tailwind and proxy configuration
│   └── src/
│       ├── api/*           # Typed API client modules, one per resource
│       ├── components/*    # App shell, navigation and shadcn/ui primitives (components/ui/)
│       └── features/*      # One folder per page: overview, alerts, agents, schedules, devices, logpage
├── docs/                   # API reference and system maintenance document
├── tests/                  # Backend test suite (pytest)
└── sample-data/            # Static camera image served by the mock raw camera route
```

### Backend

The Python code lives in `backend/`. This is the service layer and the home of application and farm-control business logic. The routers expose the REST endpoints consumed by the frontend and are registered by `main.py`.

Routers stay thin: they wire up dependencies and shape responses. The work itself lives in `backend/services/`, where functions take a database session plus plain arguments. That keeps the same logic callable from the chat agent's tools without going through HTTP: the agent in `backend/services/agent/` is built on those services, with one tool module per feature under `agent_tools/`.

Background work runs on an in-process APScheduler started from the FastAPI lifespan (`backend/schedule/`): sensor readings are polled every 30 seconds, camera images are synced hourly (and once at startup), and every saved schedule becomes a cron-triggered agent run.

### Frontend

The "frontend" refers to the React + TypeScript code in `frontend/`. Any changes should `cd` into the `frontend/` directory and run the frontend commands from there.

The dashboard uses client-side routing (`react-router-dom`) with one page per sidebar entry:

- **Overview** pins active alerts and the device proposals awaiting review, shows the camera grid, charts sensor history for a requested interval using `recharts` through shadcn chart components, and hosts the floating "Ask agent" button that opens the agent chat in a right-side sheet.
- **Alerts** manages the full alert lifecycle plus the email notification recipients and send log.
- **Agents** provides the agent chat with persisted conversation history, including read-only transcripts of scheduled runs.
- **Schedules** lists, creates and deletes recurring agent jobs.
- **Devices** manages the Kasa powerboards and the devices plugged into their outlets, with live on/off states and manual switches.
- **Logs** lists every device proposal with its review and run outcome.

The frontend UI is built with shadcn/ui source components, Tailwind CSS v4, and a basil-green theme defined in `frontend/src/styles/base.css`. Shared primitives live in `frontend/src/components/ui/`; compose those before adding custom markup or feature-local CSS.

### Application Entry Point

`main.py` is the application entry point. It creates the FastAPI app, registers the API routers, starts the scheduler and resumes any pending device auto-off timers during the application lifespan, and configures the production serving behavior for the built frontend. During development, run the backend and Vite frontend as separate servers so both support reload and hot module replacement. Leafy's version 1 API is mounted under `/api/v1`, and the Vite development server forwards `/api` requests to FastAPI without rewriting the path.

In production the built frontend is served by `SinglePageApp`, a `StaticFiles` subclass that falls back to `index.html` for unknown paths so client-side routes such as `/devices` still work on a page reload.

### Documentation

- [`docs/api-v1.md`](docs/api-v1.md) — API conventions and endpoint reference.
- [`docs/system-maintenance.md`](docs/system-maintenance.md) — operations guide: architecture, scheduled jobs, configuration, deployment and troubleshooting.
- [`AGENTS.md`](AGENTS.md) and [`frontend/AGENTS.md`](frontend/AGENTS.md) — contributor conventions.

## Getting Started for Development

### Prerequisites
Make sure you have the following installed:
- [`uv`](https://docs.astral.sh/uv/getting-started/): a CLI tool for managing Python projects. `uv` can help you install Python, manage virtual environments, install dependencies and many other things. It is the modern replacement for `pip`, `venv` and is becoming the standard for Python development.
- [`node`](https://nodejs.org/en/download/current): Node.js is necessary to run the React frontend. In production, node is not required, as the frontend is built into static files and served by the backend (FastAPI).

### Install dependencies
1. Install the Python dependencies for the backend:
```bash
uv sync
```
This will automatically download and install the required Python version (if not already installed), create a virtual environment (`.venv/`), and install required libraries.

2. Change into the frontend directory and install its dependencies.
```bash
cd frontend
npm install
```

### Configure the `.env` file.

Create a `.env` file in the root of the project using `.env.example` as a template:
```bash
cp .env.example .env
```
Edit the `.env` file to set the environment variables. The required ones:
- `ENVIRONMENT`: `development` for development or `production` for production.
- `AI_GATEWAY_API_KEY`: the API key for the Vercel AI Gateway.
- `AI_MODEL`: the model to use as the agent. See (https://vercel.com/ai-gateway/models) for available models. The model must have vision and tool-calling capabilities.
- `DATABASE_URI`: an `asyncpg` connection string for the Postgres database (a Supabase-hosted Postgres database works fine; only its database connection is used, not its Auth/BaaS features).
- `JWT_SECRET_KEY`: a random secret used to sign session tokens. Generate one with `openssl rand -hex 32`.

The remaining groups are optional; the matching feature is disabled or skipped while they are unset:
- `STUDENT_CLIENT_ID` / `STUDENT_USERNAME` / `STUDENT_PASSWORD` / `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` / `CAMERA_BUCKET`: credentials for the hourly camera image sync from the AWS API into Supabase Storage.
- `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_USE_TLS`: outgoing mail for admin notifications; sending stays disabled while the host or username is unset.
- `KASA_USERNAME` / `KASA_PASSWORD`: a TP-Link account login, only needed for powerboards whose firmware requires authentication. The server must be on the same network as the powerboards.

See `.env.example` for the full annotated list.

### Run the development servers

#### 1. Start the FastAPI server:
From the root project directory, run:
```bash
uv run uvicorn main:app --reload
```

*NOTE*: This will start the FastAPI server on `http://localhost:8000`, which is meant to only serve APIs for the frontend, therefore you should *NOT* visit this URL in your browser. The frontend development server will be running on a different port, which is where you should visit the application.

#### 2. In a separate terminal start the React (Vite) server:
```bash
cd frontend
npm run dev
```

This will start the React development server on `http://localhost:5173`, which is where you should visit the application in your browser.
Any API requests made by the frontend (e.g., `fetch('/api/some-endpoint')`) will be proxied to the FastAPI server.

In a production environment, the frontend will be built into static files and served by the backend (FastAPI). In development, however, the frontend and backend are run as separate servers to allow for live reloading of both the frontend and backend code.

## Testing and Validation

Run the backend test suite:
```bash
uv run pytest
```

Before committing backend changes, also format and lint:
```bash
uv run ruff format .
uv run ruff check .
```

For frontend changes, run from `frontend/`:
```bash
npm run lint
npm run build
```

## Production Deployment
### 1. Build the frontend:
```bash
cd frontend
npm run build
```

This will create `frontend/dist/`, which contains the static files for the frontend, which will be served by the FastAPI application.

### 2. Set the environment variable `ENVIRONMENT` to `production` in your `.env` file.

### 3. Start the FastAPI server in production mode:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
```

## Authentication and User Management

Leafy is an internal application: there is no public sign-up. Accounts are created
by an administrator using the Typer-based CLI, and users sign in with email and
password from the login page. A signed-in session is stored as an HttpOnly cookie;
the frontend never handles or stores tokens directly.

Create a user:
```bash
uv run python -m backend.cli create-user --email <email> --password <password>
```

Other available commands: `list-users`, `delete-user <user-id>` and `sync-cameras`
(runs the camera image sync on demand). Run `uv run python -m backend.cli --help`
for details.

## Some Questions You Might Have
### 1. Why separate the app into different languages (Python and JavaScript)? Why not use a single full-stack framework like `Next.js` for both the frontend and backend, this would make the project simpler and easier to maintain.

This question has been thought about and the decision to separate the project into a Python backend and a React frontend was made for the following reasons:
1. Python libraries: some of the library required to control the farm hardware such as `python-kasa`, are only available in Python, and there are no equivalent libraries in JavaScript.
2. AI/ML: this ties back to the first point, Python is the most popular language for AI/ML as it offers a wide range of libraries and tools for machine learning and data analysis. Javascript is slowly gaining traction in this area, but it is still not as mature as the Python ecosystem.