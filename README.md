# Leafy

Leafy is a full-stack web application built with React and FastAPI. It combines a modern frontend for interactive monitoring and AI-assisted workflows with a Python backend that exposes REST API endpoints, manages application logic, and integrates with external services and connected devices.

# Project Structure

Leafy is organized as one application with a Python service layer and a React user interface. The two layers are developed separately, but they live in this repository and communicate through the FastAPI API.

```text
.
├── main.py                 # FastAPI application entry point
├── backend/                # Python code and business logic
│   ├── settings.py         # Application settings
│   └── router/*            # API routers
├── frontend/               # React + TypeScript dashboard
│   ├── src/*
│   ├── public/             # Static frontend assets
│   └── vite.config.ts      # Vite development and build configuration
└── sample-data/            # Local sample camera and sensor data
```

## Backend

The Python code lives in `backend/`. This is the service layer and the home of application and farm-control business logic. The routers expose the REST endpoints consumed by the frontend and are registered by `main.py`.

## Frontend

The "frontend" refers to the React + TypeScript code in `frontend/`. It was previously managed separately in a different repository, but has been merged into this repository for easier development and deployment. Any changes should `cd` into the `frontend/` directory and run the frontend development server from there.

## Application Entry Point

`main.py` is the application entry point. It creates the FastAPI app, registers the API routers, and configures the production serving behavior for the built frontend. During development, run the backend and Vite frontend as separate servers so both support reload and hot module replacement. The API is mounted under URL `/api`, and the Vite development server proxies requests from that path to FastAPI.

# Getting Started for Development

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
Edit the `.env` file to set the environment variables as needed, some examples include:
- `ENVIRONMENT`: `development` for development or `production` for production.
- `AI_GATEWAY_API_KEY`: the API key for the Vercel AI Gateway.
- `AI_MODEL`: the model to use as the agent. See (https://vercel.com/ai-gateway/models) for available models. The model must have vision and tool-calling capabilities.

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


# Production Deployment
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

# Some Questions You Might Have
### 1. Why separate the app into different languages (Python and JavaScript)? Why not use a single full-stack framework like `Next.js` for both the frontend and backend, this would make the project simpler and easier to maintain.

This question has been thought about and the decision to separate the project into a Python backend and a React frontend was made for the following reasons:
1. Python libraries: some of the library required to control the farm hardware such as `python-kasa`, are only available in Python, and there are no equivalent libraries in JavaScript.
2. AI/ML: this ties back to the first point, Python is the most popular language for AI/ML as it offers a wide range of libraries and tools for machine learning and data analysis. Javascript is slowly gaining traction in this area, but it is still not as mature as the Python ecosystem.


# TODO

### 1. "Connect" the frontend to the backend. The frontend was prevously a separate repository and was using mocked data. The frontend should be updated to use the backend API endpoints instead of mocked data.

### 2. Clean up the frontend code and remove any unused code (mocked data, unused components, etc.). This was previously done in the separate frontend repository, but some of the unused code was reintroduced when the frontend was merged into this repository.

### 3. Implement the chat bot into the front end. See the `chatbot-prototype` branch for reference.
