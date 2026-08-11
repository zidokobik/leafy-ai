# Leafy Backend

This is a FastAPI backend application.

## Requirements

- [uv](https://docs.astral.sh/uv/) installed

## Start The App

1. Install/sync dependencies:

```bash
uv sync
```

2. Start the API server (reload mode for development):

```bash
uv run uvicorn main:app --reload
```

3. Open the API in your browser:

- App: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

## Optional: Custom Host/Port

```bash
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```
