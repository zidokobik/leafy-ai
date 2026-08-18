# Leafy AI Dashboard

A responsive React dashboard for monitoring and safely operating a Sweet basil greenhouse. The interface combines live conditions, human-authorized alert responses, adaptive schedules, device controls, a camera feed, and synchronized trends.

## Commands

- `npm install` — install dependencies
- `npm run dev` — start the local Vite server
- `npm run lint` — run ESLint
- `npm run build` — type-check and create a production build
- `npm run preview` — serve the production build locally

## Backend connection

Copy `.env.example` to `.env.local` and set `VITE_API_BASE_URL` when the backend is available. Leaving it empty keeps the current demo-data behavior.

The typed REST client lives under `src/api/`. See [docs/backend-api.md](docs/backend-api.md) for the endpoint list, request bodies, response schemas, units, and example payloads.

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
