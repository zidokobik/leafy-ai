# Leafy AI Dashboard

A responsive React dashboard for monitoring and safely operating a Sweet basil greenhouse. The interface combines live conditions, human-authorized alert responses, adaptive schedules, device controls, a camera feed, and synchronized trends.

## Commands

- `npm install` — install dependencies
- `npm run dev` — start the local Vite server
- `npm run lint` — run ESLint
- `npm run build` — type-check and create a production build
- `npm run preview` — serve the production build locally

## Environment setup

Copy the root `.env.example` to the root `.env`. Set `VITE_API_BASE_URL=/` to send API requests through the Vite development proxy.

Vite reads the root `.env` through its configured environment directory. Only values prefixed with `VITE_` are exposed to the browser.

The typed REST client lives under `src/api/`. See [the Leafy API v1 specification](../docs/api-v1.md) for the endpoint conventions and current implementation status.

## Authentication

Leafy is an internal app: there is no sign-up page. An administrator creates
accounts with the backend Typer CLI (see the root [README](../README.md)), and
the entry page only supports email/password sign-in.

On submit, the frontend calls `POST /api/v1/auth/login`. FastAPI verifies the
password and sets an HttpOnly session cookie; the browser never sees or stores a
token directly. On load, the frontend calls `GET /api/v1/users/me` to check for
an existing session cookie before opening the dashboard. Sign out calls
`POST /api/v1/auth/logout`, which clears the cookie.

Manual acceptance checks:

- Reject incorrect login credentials.
- Sign in and confirm the dashboard opens.
- Refresh the page and confirm the session is restored from the cookie.
- Stop the backend: account loading should show a retry control.
- Sign out and confirm the dashboard is no longer accessible; repeat in a second tab.

## Account settings and sign out

Open the account button in the top-right corner for **Account settings** and
**Sign out**. The button displays the saved name, falling back to the email.
Account settings supports optional first/last names, password changes, and
permanent deletion with typed email confirmation.

To verify settings, save a name, close and reopen settings, refresh, then clear
both names and check the email fallback. Change the password and verify the new
password on the next login. Cancel deletion to verify no request is sent, then
confirm deletion on a disposable account and verify the return to sign-in.


## Source structure

```text
src/
├── api/                 Typed backend contracts and REST client
├── components/          Shared shell and visual primitives
├── data/                Static dashboard configuration and sample data
├── features/
│   ├── alerts/          Human authorization workflow
│   ├── ec-dose/         EC dosing controls and live controller data
│   ├── monitoring/      Camera and synchronized trends
│   ├── overview/        Welcome and greenhouse health summary
│   └── schedule/        Adaptive schedule and manual controls
├── styles/
│   ├── base.css         Structural component styles
│   ├── theme.css        Warm natural visual theme
│   └── responsive.css   Tablet, mobile, and motion preferences
├── types/               Shared domain types
├── App.tsx              Application composition and shared alert state
└── main.tsx             React entry point
```

## Maintenance notes

- Keep cross-feature state in `App.tsx`; keep feature-local state inside its feature.
- Add reusable icons to `components/Icon.tsx`.
- Store display data and device constraints in `data/dashboard.ts` instead of duplicating values in components.
- Keep device commands gated by an explicit operator authorization state.
- Run both `npm run lint` and `npm run build` after changes.
# LeafyAI_team-Sprouts
