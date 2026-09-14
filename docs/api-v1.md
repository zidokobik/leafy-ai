# Leafy API v1

This document is the source of truth for Leafy's public HTTP API conventions and implementation status.

## Routing

- Every Leafy API endpoint starts with `/api/v1`.
- The browser, Vite development proxy, and FastAPI use the same path. The proxy does not rewrite or remove `/api`.
- FastAPI routes contain the real `/api/v1` prefix. `root_path` is reserved for a future deployment behind a reverse proxy and is not used by the current application.
- During development, Vite forwards `/api` requests to `http://localhost:8000`.
- Setting `VITE_API_BASE_URL=/` enables same-origin API requests through the Vite proxy. Leaving it empty keeps the frontend in demo mode.

Example request flow:

```text
Browser  GET /api/v1/water-sensor/readings
Vite     GET /api/v1/water-sensor/readings
FastAPI  GET /api/v1/water-sensor/readings
```

## Data conventions

- JSON fields exposed to the React frontend use `camelCase`.
- Python identifiers use `snake_case` internally and map to the public JSON field names at the API boundary.
- Timestamps use ISO 8601 in UTC, for example `2026-09-01T10:42:00Z`.
- Unit-bearing numeric fields include the unit in the field name, for example `temperatureC`, `humidityPercent`, and `nutrientEcMicrosiemens`.
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

## Implemented endpoints

The current backend implementations are mocks. They now share the `/api/v1` namespace, but their existing response bodies have not yet been migrated to the public camelCase conventions above.

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
| `GET` | `/api/v1/historical-data/` | Returns generic hardcoded historical records |
| `POST` | `/api/v1/auth/login` | Verifies email/password and sets the session cookie |
| `POST` | `/api/v1/auth/logout` | Clears the session cookie |
| `GET` | `/api/v1/users/me` | Verifies the session cookie and returns the user's profile |

## Reserved frontend contracts

The typed frontend client already reserves the following v1 paths. They are part of the target contract but are not implemented by the current backend. Until each endpoint is implemented, the frontend must remain in demo mode or handle the unavailable endpoint explicitly.

| Method | Path | Status |
| --- | --- | --- |
| `GET` | `/api/v1/schedule` | Not implemented |
| `PUT` | `/api/v1/schedule/manual-mode` | Not implemented |
| `POST` | `/api/v1/schedule/reset` | Not implemented |
| `PUT` | `/api/v1/schedule/recommendation` | Not implemented |
| `PATCH` | `/api/v1/devices/{device}` | Not implemented |
| `PUT` | `/api/v1/alerts/ec/decision` | Not implemented |
| `GET` | `/api/v1/ec-dose` | Not implemented |
| `PUT` | `/api/v1/ec-dose/settings` | Not implemented |
| `GET` | `/api/v1/monitoring/latest` | Not implemented |
| `GET` | `/api/v1/monitoring/history?range={range}` | Not implemented (temporarily disabled while auth is reworked; previously read Supabase `sensor_data`) |

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

The current account endpoints are:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/users/me` | Implemented: read the authenticated user's profile |
| `PATCH` | `/api/v1/users/me` | Implemented: update only firstName and lastName |
| `PUT` | `/api/v1/users/me/password` | Implemented: change the authenticated user's password |
| `DELETE` | `/api/v1/users/me` | Implemented: permanently delete the authenticated account |

## Account settings

`PATCH /api/v1/users/me` accepts `firstName` and `lastName` only (maximum 100
characters each). Omitted fields are unchanged; null, empty or whitespace-only
names clear the field. Other fields, including email and user IDs, return
422. The response is the same profile shape as GET, with a fresh `updatedAt`.

`PUT /api/v1/users/me/password` accepts `{ "newPassword": "..." }` (minimum 8
characters) and re-hashes it with Argon2. It returns 204 with no body.

`DELETE /api/v1/users/me` deletes the user row and returns 204 with no body. The
client asks for the account email as confirmation before sending the request.
