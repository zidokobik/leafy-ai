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
| `GET` | `/api/v1/users/me` | Verifies a Supabase access token and returns the user's profile and roles |

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
| `GET` | `/api/v1/monitoring/history?range={range}` | Implemented: reads shared `sensor_data` history (`24H`, `7D`, or `30D`) |

## Authentication and account contracts

The React application signs up, signs in, and signs out directly through Supabase Auth. Leafy does not duplicate those operations under `/api/v1/auth/*`.

Protected Leafy endpoints receive the Supabase access token in the request header:

```http
Authorization: Bearer <access-token>
```

FastAPI verifies the token, uses its `sub` claim as the authenticated user's ID, and queries `public.users` plus the role tables with a server-only Supabase secret key. The browser must never receive that secret key.

The current and planned account endpoints are:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/users/me` | Implemented: read the authenticated user's profile and roles |
| `PATCH` | `/api/v1/users/me` | Implemented: update only firstName and lastName |
| `DELETE` | `/api/v1/users/me` | Implemented: permanently delete the authenticated account; apply the deletion SQL migration first |
| `GET` | `/api/v1/admin/users` | List users as an administrator |
| `PATCH` | `/api/v1/admin/users/{userId}` | Update a user's application role as an administrator |
| `DELETE` | `/api/v1/admin/users/{userId}` | Delete a user as an administrator |

Permission checks for `viewer`, `operator`, and `admin` are the next backend layer; the current endpoint verifies identity and returns assigned roles but does not yet authorize device operations by role.

## Account settings

`PATCH /api/v1/users/me` accepts `firstName` and `lastName` only (maximum 100
characters each). Omitted fields are unchanged; null, empty or whitespace-only
names clear the field. Other fields, including roles, email and user IDs, return
422. The response is the same profile shape as GET, with a fresh `updatedAt`.

Password changes use Supabase Auth `updateUser({ password })` directly, including
email reauthentication when Supabase requires it. Passwords are not stored in
`public.users` or sent to the Leafy profile API.

`DELETE /api/v1/users/me` calls the server-only Supabase Auth admin API with the
authenticated token's subject, and returns 204 with no body. The client asks for
the account email as confirmation before sending the request. Failed upstream
deletion returns 503 and does not trigger separate profile or role deletions.

Before enabling live deletion, run [account-deletion.sql](sql/account-deletion.sql)
in the Supabase SQL Editor. It changes the existing foreign keys so that deleting
an Auth account cascades to its profile and role memberships, while `assigned_by`
references become null and other people's role assignments remain intact.
All changes happen inside a transaction. Review additional foreign keys using the
query at the end; storage ownership or other restrictive references can still block
deletion. The migration is provided in the repository, not automatically applied.

## Monitoring history

`GET /api/v1/monitoring/history?range=24H` requires a Supabase access token. It
reads `public.sensor_data` with the server-only Supabase key, filters by the
sensor's `created_at`, and returns the same rows to every authenticated user.
The response uses camelCase names (`waterTemperatureC`, `reservoirLevelCm`,
`irrigationPumpOn`, etc.); timestamps are rendered in Melbourne time by the
frontend. The frontend refreshes this endpoint every 30 minutes for the 24H,
7D, and 30D range tabs.
