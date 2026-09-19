# Repository Guidelines

## Project Structure & Module Organization

This repository is a React 19 dashboard built with TypeScript and Vite.

- `src/main.tsx` mounts the application and loads the global stylesheets.
- `src/App.tsx` gates the app on authentication, then declares the client-side routes.
- `src/api/` holds the fetch wrapper, environment config, shared response types and the typed endpoint clients.
- `src/components/` holds the shell (`AppShell`, `AppSidebar`, `Topbar`) and small shared pieces. `navigation.ts` is the single source of truth for the sidebar entries and page titles.
- `src/features/<feature>/` holds one folder per feature, each containing its page component plus the hooks, child components and styles it owns.
- `src/styles/` holds the global stylesheets: `base.css` (tokens and resets), `shell.css` (app shell) and `pages.css` (page and chart layout).
- `src/assets/` stores images imported by TypeScript modules.
- `vite.config.ts` and `tsconfig*.json` define build and TypeScript behavior.

Add a new page by creating a feature folder with its page component, registering the route in `src/App.tsx`, and adding the sidebar entry to `src/components/navigation.ts`.

Routing is history based (`BrowserRouter`), so any production host must fall back to `index.html` for unknown paths. `main.py` already does this.

## Build, Test, and Development Commands

- `npm install` installs the exact dependency tree from `package-lock.json`.
- `npm run dev` starts the Vite development server with hot module replacement.
- `npm run build` runs TypeScript project checks and creates a production bundle in `dist/`.
- `npm run lint` checks TypeScript and React code with ESLint.
- `npm run preview` serves the production build locally for final verification.

Run `npm run lint` and `npm run build` before submitting changes.

## Coding Style & Naming Conventions

Use TypeScript and functional React components. Follow the existing style: two-space indentation, single quotes, no semicolons, and trailing commas where supported. Use `PascalCase` for components and component files, `camelCase` for variables and functions, and descriptive kebab-case names for CSS classes. Keep imports grouped at the top and remove unused declarations; TypeScript and ESLint enforce these rules.

Data fetching lives in a hook next to the feature that needs it. Hooks own their own `AbortController`, clean up on unmount, and expose a `status` value rather than a bare boolean so loading, ready and error states stay distinct.

API response fields are `camelCase` and measurements are nullable, matching `docs/api-v1.md`. Do not assume a measurement is present.

## Testing Guidelines

No automated test framework or coverage target is currently configured. Validate every change with linting, a production build, and manual browser checks through `npm run dev`. If tests are introduced, prefer colocated names such as `ComponentName.test.tsx` and add the corresponding test command to `package.json`.

## Commit & Pull Request Guidelines

Git history is not included in this checkout, so no repository-specific commit convention can be inferred. Use concise, imperative subjects such as `Add dashboard navigation` and keep each commit focused. Pull requests should explain the change, list validation performed, link relevant issues, and include screenshots or recordings for visible UI changes. Call out new dependencies, configuration changes, or known follow-up work.

## Security & Configuration

Do not commit secrets or local environment files. The root `.env` is the shared configuration source for the frontend and backend. Expose browser-safe variables only through Vite's `VITE_` or `PUBLIC_` prefixes, document required values, and keep sensitive credentials on the server side.
