# Leafy AI Dashboard

A responsive React dashboard for monitoring and safely operating a Sweet basil greenhouse. The interface combines live conditions, human-authorized alert responses, adaptive schedules, device controls, a camera feed, and synchronized trends.

## Commands

- `npm install` — install dependencies
- `npm run dev` — start the local Vite server
- `npm run lint` — run ESLint
- `npm run build` — type-check and create a production build
- `npm run preview` — serve the production build locally

## Environment setup

Copy `.env.example` to `.env.local`. Set `VITE_API_BASE_URL=/` to send API requests through the Vite development proxy, and provide `VITE_SUPABASE_URL` plus `VITE_SUPABASE_PUBLISHABLE_KEY` for Supabase Auth.

Only the browser-safe Supabase publishable key belongs in `frontend/.env.local`. Keep the Supabase secret key in the backend root `.env`.

The typed REST client lives under `src/api/`. See [the Leafy API v1 specification](../docs/api-v1.md) for the endpoint conventions and current implementation status.

## Authentication

The entry page supports email/password sign-up and sign-in through Supabase Auth.
The SDK restores sessions and refreshes tokens. FastAPI verifies the access token
at `GET /api/v1/users/me` before the dashboard opens; roles come from that response.
Sign out ends the session on this browser. Device authorization on the backend
is still separate work; UI role checks are not a security boundary.

Enable the Email provider in Supabase Auth. In Authentication > URL Configuration,
set the production Site URL and allow the frontend origins used for confirmation
redirects (for example `http://localhost:5173` during development).
If email confirmation is enabled, users must follow the email link before signing in.
Start FastAPI on port 8000 and Vite on port 5173 for local testing. The dashboard's
monitoring and device API implementations remain separate from authentication.

Manual acceptance checks:

- Register with matching passwords; verify the email confirmation message.
- Reject mismatched passwords and incorrect login credentials.
- Confirm email, sign in, and check that `/api/v1/users/me` receives a Bearer token.
- Refresh the page and confirm the session is restored.
- Stop the backend: account loading should show retry and sign-out controls.
- Sign out and confirm the dashboard is no longer accessible; repeat in a second tab.

## Account settings and sign out

Open the account button in the top-right corner for **Account settings** and
**Sign out**. The button displays the saved name, falling back to the email.
Account settings supports optional first/last names, password changes (and email
security codes when required), and permanent deletion with typed email confirmation.

Before testing deletion, apply `../docs/sql/account-deletion.sql` in Supabase SQL
Editor. See `../docs/api-v1.md` for the required foreign-key behavior. Test deletion
only with a disposable account. Check that its Auth user, public profile and role
memberships disappear, and that other users' roles are preserved.

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
