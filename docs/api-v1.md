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

| Operation                              | Success status   |
| -------------------------------------- | ---------------- |
| Read a resource                        | `200 OK`         |
| Create a resource                      | `201 Created`    |
| Replace or partially update a resource | `200 OK`         |
| Delete without a response body         | `204 No Content` |

Common errors use `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `409 Conflict`, `422 Unprocessable Content`, and `500 Internal Server Error` as appropriate.

## Sensor endpoints

These are the only endpoints the dashboard currently calls. Both require a session cookie and read
the Postgres `sensor_data` table through `backend/services/sensors.py`.

| Method | Path                                                       | Behavior                                                                                    |
| ------ | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| `GET`  | `/api/v1/sensors/history?before={ISO 8601}&end={ISO 8601}` | Readings in the inclusive interval, averaged into adaptive buckets and ordered oldest first |
| `GET`  | `/api/v1/sensors/latest`                                   | The most recent raw reading, or `404` when the table is empty                               |

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

## Alerts

Stateful dashboard alerts raised by the agent. The Overview page pins active alerts at the top and
polls this endpoint on the sensor interval; the Alerts page manages the full lifecycle. Alerts are
deduplicated by `alertKey`, a stable snake_case condition id (for example `water_ph_high`): at most
one **active** alert exists per key, and re-raising the same key updates that alert in place and
increments `occurrences` instead of creating a new row, so repeated scheduled agent runs cannot
stack duplicates. All endpoints require a session cookie.

Dismissing and resolving are distinct. Dismissing only hides an active alert from the Overview pin
(it stays active, and a re-raise clears the dismissal so the alert resurfaces). Resolving is the
explicit close action, performed by the agent's `resolve_alert` tool or a user on the Alerts page.

| Method | Path                                | Behavior                                                                                                              |
| ------ | ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `GET`  | `/api/v1/alerts?status={filter}`    | List alerts ordered critical first, then most recently raised. `status` is `active` (default), `resolved`, or `all`; supports `limit` (1-100, default 50) and `offset` |
| `POST` | `/api/v1/alerts/{alertId}/dismiss`  | Hide an active alert from the Overview pin without resolving it. Idempotent; unknown ids return `404`                   |
| `POST` | `/api/v1/alerts/{alertId}/resolve`  | Explicitly mark an alert resolved. Idempotent; unknown ids return `404`                                                 |

```json
[
  {
    "alertId": "7a75a45e-8b30-4f65-9df3-f306eb52e4a0",
    "alertKey": "water_ph_high",
    "severity": "warning",
    "title": "Water pH trending high",
    "message": "pH has risen from 6.1 to 7.2 over the last 6 hours.",
    "status": "active",
    "occurrences": 3,
    "scheduleId": "0b7ad34e-98f9-4a3c-8a47-0e6f27de9a1c",
    "createdAt": "2026-09-30T06:00:00Z",
    "updatedAt": "2026-09-30T10:00:00Z",
    "resolvedAt": null,
    "resolvedBy": null,
    "dismissedAt": null
  }
]
```

`severity` is `info`, `warning`, or `critical`. `scheduleId` records which scheduled job last
raised the alert (`null` for interactive chat raises or deleted schedules). `dismissedAt` is set by
the dismiss endpoint and cleared by a re-raise; the Overview pin only shows active alerts where it
is `null`. `resolvedBy` is `"agent"` when the agent's `resolve_alert` tool verified the condition
cleared and `"user"` when someone resolved the alert on the Alerts page. A resolved key can be
raised again later as a fresh alert with its own history.

The agent manages alerts through the `list_alerts`, `raise_alert`, `update_alert`, and
`resolve_alert` tools, which call `backend/services/alerts.py` directly (`update_alert` edits an
active alert's severity, title, or message without counting a new occurrence). There is no HTTP
endpoint for creating alerts; the dashboard only reads, dismisses, and resolves them. Raising an
alert notifies no one by itself; the agent escalates critical conditions by email (see Email
notifications below).

## Email notifications

The agent can email the farm's admins through its `send_email` tool, which calls
`backend/services/emails.py` directly. The agent is prompt-guided to email only critical
escalations and explicitly requested reports (for example a scheduled daily summary). SMTP
credentials live in the server's `.env` (`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`,
`SMTP_PASSWORD`, `SMTP_USE_TLS`) and are never exposed over HTTP; mail is always sent as
`Leafy AI <SMTP_USERNAME>`, and sending stays disabled while `SMTP_HOST` or `SMTP_USERNAME` is
empty. The Alerts page manages the admin recipient list and shows the send log; every send
attempt is logged, including failures. There is no HTTP endpoint for composing emails besides the
test endpoint. All endpoints require a session cookie.

| Method   | Path                                         | Behavior                                                                                             |
| -------- | -------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `GET`    | `/api/v1/notifications/recipients`           | List recipients, oldest first                                                                           |
| `POST`   | `/api/v1/notifications/recipients`           | Add a recipient (`{ "email": "...", "label": "..." }`, label optional); duplicates return `409`         |
| `PATCH`  | `/api/v1/notifications/recipients/{id}`      | Enable or disable a recipient (`{ "enabled": true }`); unknown ids return `404`                         |
| `DELETE` | `/api/v1/notifications/recipients/{id}`      | Remove a recipient; returns `204 No Content`                                                            |
| `GET`    | `/api/v1/notifications/emails`               | Email send log, most recent first; supports `limit` (1-100, default 50) and `offset`                    |
| `POST`   | `/api/v1/notifications/emails/test`          | Send a test email to all enabled recipients; `503` when SMTP is unconfigured, `400` with no recipients  |

```json
[
  {
    "emailId": "64dbb326-2f52-4a51-a548-55a21e843b16",
    "recipients": ["admin@example.com"],
    "subject": "Water pH critically high",
    "status": "sent",
    "error": null,
    "scheduleId": null,
    "triggeredBy": "agent",
    "createdAt": "2026-10-11T08:00:00Z"
  }
]
```

`status` is `sent` or `failed` (`error` carries the SMTP failure). `triggeredBy` is `"agent"` for
the agent's `send_email` tool and `"user"` for test emails from the Alerts page. `scheduleId`
records the scheduled run that triggered the send (`null` for interactive chat sends, test emails,
or deleted schedules).

## Scheduled agent jobs

Scheduled agent jobs require a session cookie and persist a title, agent instruction, and standard
five-field cron expression. A successful create request registers the job with the running
APScheduler instance immediately; startup also restores every persisted job.

| Method   | Path                        | Behavior                                                                                                       |
| -------- | --------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `GET`    | `/api/v1/schedules`         | List scheduled agent jobs, newest first                                                                        |
| `POST`   | `/api/v1/schedules`         | Create and immediately register a scheduled agent job; returns `201 Created`                                   |
| `PATCH`  | `/api/v1/schedules/{jobId}` | Update a scheduled job's title, instruction, and cron expression, replacing its running scheduler registration |
| `DELETE` | `/api/v1/schedules/{jobId}` | Remove a scheduled job from persistence and the running scheduler; returns `204 No Content`                    |

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

## Agent chat and conversation history

The agent chat streams AI SDK UI server-sent events and persists every completed exchange. All
chat endpoints require a session cookie.

| Method   | Path                                        | Behavior                                                                     |
| -------- | ------------------------------------------- | ---------------------------------------------------------------------------- |
| `POST`   | `/api/v1/chat`                              | Run the chat agent and stream the response as AI SDK UI SSE                  |
| `GET`    | `/api/v1/chat/conversations`                | List stored conversations, most recently updated first                       |
| `GET`    | `/api/v1/chat/conversations/{conversationId}` | One conversation with its messages in AI SDK UI format, or `404`           |
| `DELETE` | `/api/v1/chat/conversations/{conversationId}` | Delete a conversation and its messages; returns `204 No Content`           |

`POST /api/v1/chat` accepts `{ "id": "<uuid>", "messages": [...] }`, where `id` is a
client-generated conversation UUID and `messages` is the full AI SDK UI message history. After the
stream completes, the server stores the complete run history under that id, creating the
conversation on first use (its title is derived from the first user message) and replacing the
stored messages on follow-up turns. Server-side system prompts are never stored or returned. A
response that fails or is aborted mid-stream is not persisted.

Each scheduled agent job execution is also stored as its own conversation with `source` set to
`"schedule"`, the schedule's title, and its `scheduleId`. Deleting a schedule keeps its
conversations and nulls `scheduleId`. The dashboard shows scheduled conversations read-only.

A conversation summary looks like:

```json
{
  "id": "9f1dea9e-676a-4155-9da2-2ac62cde523c",
  "title": "Summarize the latest 24 hours sensor data",
  "source": "chat",
  "scheduleId": null,
  "createdAt": "2026-09-29T01:02:03Z",
  "updatedAt": "2026-09-29T01:04:05Z"
}
```

The detail response adds `messages`, an array of AI SDK UI `UIMessage` objects (`id`, `role`,
`parts`, `metadata`) that `useChat` can consume directly as initial messages. Conversations are
stored in the `chat_conversations` and `chat_messages` tables as serialized runtime messages and
converted to UI messages on read by `backend/services/chat_history.py`.

## Camera images

An hourly scheduler job (also run once at startup) logs in to the AWS's Cognito app client,
requests fresh presigned links from the tutor's image API, and copies each image into the public
Supabase Storage bucket `CAMERA_BUCKET` as `<cameraId>.jpg`. The permanent link and capture time are
stored in the `cameras` table; images whose `captured_at` has not changed are skipped. Run a sync on
demand with `uv run python -m backend.cli sync-cameras`.

| Method | Path                    | Behavior                                                                |
| ------ | ----------------------- | ----------------------------------------------------------------------- |
| `GET`  | `/api/v1/camera/latest` | Latest image for every camera, ordered by id. Requires a session cookie |

```json
[
  {
    "id": "level1_camera1",
    "label": "Level 1 · Camera 1",
    "imageUrl": "https://<project>.supabase.co/storage/v1/object/public/images/level1_camera1.jpg?t=1790409600",
    "capturedAt": "2026-09-26T08:00:00Z"
  }
]
```

`imageUrl` is null until the camera's first successful sync. The `?t=` query changes with each new
capture so browsers do not show a cached image.

## Hardware endpoints

These are still mock implementations that return hardcoded values. They are kept as the integration
points for real hardware and are not yet used by the dashboard.

| Method | Path                                  | Current behavior              |
| ------ | ------------------------------------- | ----------------------------- |
| `GET`  | `/api/v1/camera/raw/{level}/{camera}` | Returns a static sample image |

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

| Method   | Path                        | Purpose                                                |
| -------- | --------------------------- | ------------------------------------------------------ |
| `POST`   | `/api/v1/auth/login`        | Verify email and password, then set the session cookie |
| `POST`   | `/api/v1/auth/logout`       | Clear the session cookie                               |
| `GET`    | `/api/v1/users/me`          | Read the authenticated user's profile                  |
| `PATCH`  | `/api/v1/users/me`          | Update only firstName and lastName                     |
| `PUT`    | `/api/v1/users/me/password` | Change the authenticated user's password               |
| `DELETE` | `/api/v1/users/me`          | Permanently delete the authenticated account           |

## Account settings

`PATCH /api/v1/users/me` accepts `firstName` and `lastName` only (maximum 100
characters each). Omitted fields are unchanged; null, empty or whitespace-only
names clear the field. Other fields, including email and user IDs, return 422. The response is the same profile shape as GET, with a fresh `updatedAt`.

`PUT /api/v1/users/me/password` accepts `{ "newPassword": "..." }` (minimum 8
characters) and re-hashes it with Argon2. It returns 204 with no body.

`DELETE /api/v1/users/me` deletes the user row and returns 204 with no body. The
client asks for the account email as confirmation before sending the request.
