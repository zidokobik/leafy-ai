# Leafy API v1

This document is the source of truth for Leafy's public HTTP API conventions and implementation status.

## Routing

- Every Leafy API endpoint starts with `/api/v1`.
- The browser, Vite development proxy, and FastAPI use the same path. The proxy does not rewrite or remove `/api`.
- FastAPI routes contain the real `/api/v1` prefix. `root_path` is reserved for a future deployment behind a reverse proxy and is not used by the current application.
- During development, Vite forwards `/api` requests to `http://localhost:8000`.
- `VITE_API_BASE_URL` is optional. Leave it empty (or set it to `/`) to send same-origin requests, which the Vite proxy forwards to FastAPI. Set an absolute URL only when the frontend is served from a different origin than the API.

Example request flow:

```text
Browser  GET /api/v1/sensors/history?before=2026-09-18T05%3A08%3A00Z&end=2026-09-19T05%3A08%3A00Z
Vite     GET /api/v1/sensors/history?before=2026-09-18T05%3A08%3A00Z&end=2026-09-19T05%3A08%3A00Z
FastAPI  GET /api/v1/sensors/history?before=2026-09-18T05%3A08%3A00Z&end=2026-09-19T05%3A08%3A00Z
```

## Data conventions

- JSON fields exposed to the React frontend use `camelCase`.
- Python identifiers use `snake_case` internally and map to the public JSON field names at the API boundary.
- Timestamps use ISO 8601 in UTC, for example `2026-09-01T10:42:00Z`.
- Unit-bearing numeric fields keep the unit suffix used by the database columns, for example `ambientTempC`, `humidityPct`, and `ecUsCm`.
- Measurements are nullable. A reading can be missing individual fields, so clients must handle `null`.
- FastAPI's standard error body is used unless a feature requires a more specific contract:

```json
{
  "detail": "Resource not found"
}
```

## Status codes

| Operation | Success status |
| --- | --- |
| Read a resource | `200 OK` |
| Create a resource | `201 Created` |
| Replace or partially update a resource | `200 OK` |
| Delete without a response body | `204 No Content` |

Common errors use `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `409 Conflict`, `422 Unprocessable Content`, and `500 Internal Server Error` as appropriate.

## Sensor endpoints

These are the only endpoints the dashboard currently calls. Both require a session cookie and read
the Postgres `sensor_data` table through `backend/services/sensors.py`.

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/v1/sensors/history?before={ISO 8601}&end={ISO 8601}` | Readings in the inclusive interval, averaged into adaptive buckets and ordered oldest first |
| `GET` | `/api/v1/sensors/latest` | The most recent raw reading, or `404` when the table is empty |

`before` and `end` are required UTC ISO 8601 timestamps. `before` must be earlier than `end`; an
invalid interval returns `422 Unprocessable Content`. Both bounds are inclusive.

Sensors are polled every 30 seconds, so a raw long interval can contain tens of thousands of rows.
`/history` selects the smallest standard bucket that targets at most about 200 points. Available
bucket sizes range from one minute to one day; the selected size is included in each response.

`/history` returns the bucket size so clients do not have to infer it:

```json
{
  "before": "2026-09-18T05:08:00Z",
  "end": "2026-09-19T05:08:00Z",
  "bucketSeconds": 300,
  "readings": [
    {
      "timestamp": "2026-09-19T05:05:00Z",
      "waterPh": 6.1,
      "ecUsCm": 2648.75,
      "waterTempC": 23.55,
      "ambientTempC": 22.84,
      "humidityPct": 54.33,
      "reservoirLevelCm": 13.58
    }
  ]
}
```

A bucketed reading is an average, so `/latest` is the endpoint to use for a current value.

`backend/services/sensors.py` takes an `AsyncSession` plus plain arguments rather than FastAPI
dependencies, so agent tools can call the same functions without going through HTTP.

## Scheduled agent jobs

Scheduled agent jobs require a session cookie and persist a title, agent instruction, and standard
five-field cron expression. A successful create request registers the job with the running
APScheduler instance immediately; startup also restores every persisted job.

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/api/v1/schedules` | List scheduled agent jobs, newest first |
| `POST` | `/api/v1/schedules` | Create and immediately register a scheduled agent job; returns `201 Created` |
| `PATCH` | `/api/v1/schedules/{jobId}` | Update a scheduled job's title, instruction, and cron expression, replacing its running scheduler registration |
| `DELETE` | `/api/v1/schedules/{jobId}` | Remove a scheduled job from persistence and the running scheduler; returns `204 No Content` |

`POST /api/v1/schedules` accepts the following body:

```json
{
  "title": "Morning farm report",
  "instruction": "Report the current system status.",
  "cronExpression": "0 6 * * *"
}
```

`title`, `instruction`, and `cronExpression` must not be blank. `cronExpression` must be a valid
five-field crontab expression. Invalid values return `422 Unprocessable Content`.

`PATCH /api/v1/schedules/{jobId}` accepts
`{ "title": "...", "instruction": "...", "cronExpression": "..." }`. All values are required
and use the same validation as creation. A successful update takes effect immediately in the
running scheduler.

## Hardware endpoints

These are still mock implementations that return hardcoded values. They are kept as the integration
points for real hardware and are not yet used by the dashboard.

| Method | Path | Current behavior |
| --- | --- | --- |
| `GET` | `/api/v1/camera/raw/{level}/{camera}` | Returns a static sample image |

Their response bodies have not been migrated to the camelCase conventions above.

## Authentication and account contracts

Leafy is an internal application with no public sign-up. Accounts are created by
an administrator using the Typer CLI (`uv run python -m backend.cli create-user`).
The frontend only exposes a sign-in page.

`POST /api/v1/auth/login` accepts `{ "email": "...", "password": "..." }`, verifies
the password (Argon2 via `pwdlib`), and sets an HttpOnly, `SameSite=Lax` session
cookie containing a signed JWT (`JWT_SECRET_KEY`, HS256). `POST /api/v1/auth/logout`
clears that cookie. Every other endpoint under `/api/v1` that requires
authentication reads the session cookie; the browser never receives the token
directly and no `Authorization` header is used.

The cookie is also marked `Secure` whenever `ENVIRONMENT=production`, which
requires the app to be served over HTTPS. Browsers silently discard `Secure`
cookies sent over plain HTTP, which looks like login succeeding but the session
not surviving a page reload. Set `SESSION_COOKIE_SECURE=false` only if you are
temporarily deploying without TLS.

There is a single account tier: every signed-in user has full access. There are
no per-user roles to manage.

The current session and account endpoints are:

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Verify email and password, then set the session cookie |
| `POST` | `/api/v1/auth/logout` | Clear the session cookie |
| `GET` | `/api/v1/users/me` | Read the authenticated user's profile |
| `PATCH` | `/api/v1/users/me` | Update only firstName and lastName |
| `PUT` | `/api/v1/users/me/password` | Change the authenticated user's password |
| `DELETE` | `/api/v1/users/me` | Permanently delete the authenticated account |

## Account settings

`PATCH /api/v1/users/me` accepts `firstName` and `lastName` only (maximum 100
characters each). Omitted fields are unchanged; null, empty or whitespace-only
names clear the field. Other fields, including email and user IDs, return
422. The response is the same profile shape as GET, with a fresh `updatedAt`.

`PUT /api/v1/users/me/password` accepts `{ "newPassword": "..." }` (minimum 8
characters) and re-hashes it with Argon2. It returns 204 with no body.

`DELETE /api/v1/users/me` deletes the user row and returns 204 with no body. The
client asks for the account email as confirmation before sending the request.
