# Leafy AI Dashboard

A responsive React dashboard for monitoring a Sweet basil hydroponic farm and supporting AI-assisted growing workflows. It provides authenticated access, sensor history, agent chat, and recurring agent schedule management; device controls remain planned.

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

## UI system

The frontend uses shadcn/ui with Tailwind CSS v4. The shadcn configuration lives in `components.json`, shared primitives live in `src/components/ui/`, and Tailwind/theme tokens live in `src/styles/base.css`.

Use shadcn primitives for common UI instead of custom component CSS:

- App chrome: `Sidebar`, `DropdownMenu`, `Avatar`, `Separator`, `TooltipProvider`.
- Forms and account settings: `Field`, `Input`, `Textarea`, `Button`, `Alert`, `Dialog`.
- Dashboard content: `Card`, `ToggleGroup`, `Skeleton`, `Empty`, and `Chart` wrappers around Recharts.

Add shadcn components from the frontend directory:

```bash
npx shadcn@latest add <component>
```

Keep broad theme changes in `src/styles/base.css`. The current palette uses basil greens, mint surfaces and hydroponic chart accents via semantic tokens such as `--background`, `--primary`, `--sidebar`, and `--chart-*`.

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

Open the account button in the sidebar footer for **Account settings** and
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
├── assets/              Imported images and static frontend assets
├── components/          App shell and shared shadcn/ui primitives
├── features/
│   ├── agents/          Interactive farm agent chat
│   ├── auth/            Login, session state and account settings
│   ├── devices/         Placeholder for device controls
│   ├── overview/        Sensor history charts and range controls
│   └── schedules/       Agent schedule management
├── hooks/               Shared React hooks used by shadcn components
├── lib/                 Shared utilities such as `cn`
├── styles/base.css      Tailwind imports, shadcn tokens and global theme
├── App.tsx              Auth gate and route declarations
└── main.tsx             React entry point
```

## Maintenance notes

- Keep routers/pages thin: feature-specific data fetching belongs in hooks next to the feature that uses it.
- Add new routes in `src/App.tsx` and sidebar entries in `src/components/navigation.ts`.
- Use Lucide icons directly in components and navigation entries.
- Compose from shadcn primitives before introducing feature-local CSS.
- Run both `npm run lint` and `npm run build` after changes.
