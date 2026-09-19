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
Browser  GET /api/v1/sensors/history?range=24h
Vite     GET /api/v1/sensors/history?range=24h
FastAPI  GET /api/v1/sensors/history?range=24h
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
| `GET` | `/api/v1/sensors/history?range={range}` | Readings for `24h`, `7d` or `30d`, averaged into buckets and ordered oldest first |
| `GET` | `/api/v1/sensors/latest` | The most recent raw reading, or `404` when the table is empty |

Sensors are polled every 30 seconds, so a raw 30 day range would be roughly 86,000 rows. `/history`
averages each range into fixed buckets instead, which keeps a response near 200 points:

| Range | Bucket | Approximate points |
| --- | --- | --- |
| `24h` | 5 minutes | 288 |
| `7d` | 1 hour | 168 |
| `30d` | 4 hours | 180 |

`/history` returns the bucket size so clients do not have to infer it:

```json
{
  "range": "24h",
  "start": "2026-09-18T05:08:00Z",
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
dependencies, so the planned chat agent can call the same functions as tools without going through
HTTP.

## Hardware endpoints

These are still mock implementations that return hardcoded values. They are kept as the integration
points for real hardware and are not yet used by the dashboard.

| Method | Path | Current behavior |
| --- | --- | --- |
| `GET` | `/api/v1/water-sensor/readings` | Returns hardcoded water-sensor readings |
| `GET` | `/api/v1/water-sensor/health` | Returns hardcoded sensor health |
| `GET` | `/api/v1/camera/raw/{level}/{camera}` | Returns a static sample image |
| `GET` | `/api/v1/controller/fan` | Returns mock fan status |
| `PUT` | `/api/v1/controller/fan?on={boolean}` | Returns the requested mock fan status |
| `GET` | `/api/v1/controller/lights` | Returns mock light status |
| `PUT` | `/api/v1/controller/lights?on={boolean}` | Returns the requested mock light status |
| `GET` | `/api/v1/controller/pump` | Returns mock pump status |
| `PUT` | `/api/v1/controller/pump?on={boolean}` | Returns the requested mock pump status |
| `GET` | `/api/v1/controller/ph_doser` | Returns mock pH doser status |
| `PUT` | `/api/v1/controller/ph_doser?on={boolean}` | Returns the requested mock pH doser status |
| `GET` | `/api/v1/controller/ec_doser` | Returns mock EC doser status |
| `PUT` | `/api/v1/controller/ec_doser?on={boolean}` | Returns the requested mock EC doser status |

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
