# Repository Guidelines

## Project Structure & Module Organization

This repository is a React 19 dashboard built with TypeScript and Vite.

- `src/main.tsx` mounts the application.
- `src/App.tsx` contains the primary UI component.
- `src/*.css` holds global and component-level styles.
- `src/assets/` stores images imported by TypeScript modules.
- `public/` contains static files served from the site root.
- `vite.config.ts` and `tsconfig*.json` define build and TypeScript behavior.

Keep new components under `src/`, grouping related component, style, and test files in a clearly named directory as the application grows.

## Build, Test, and Development Commands

- `npm install` installs the exact dependency tree from `package-lock.json`.
- `npm run dev` starts the Vite development server with hot module replacement.
- `npm run build` runs TypeScript project checks and creates a production bundle in `dist/`.
- `npm run lint` checks TypeScript and React code with ESLint.
- `npm run preview` serves the production build locally for final verification.

Run `npm run lint` and `npm run build` before submitting changes.

## Coding Style & Naming Conventions

Use TypeScript and functional React components. Follow the existing style: two-space indentation, single quotes, no semicolons, and trailing commas where supported. Use `PascalCase` for components and component files, `camelCase` for variables and functions, and descriptive kebab-case names for CSS classes. Keep imports grouped at the top and remove unused declarations; TypeScript and ESLint enforce these rules.

## Testing Guidelines

No automated test framework or coverage target is currently configured. Validate every change with linting, a production build, and manual browser checks through `npm run dev`. If tests are introduced, prefer colocated names such as `ComponentName.test.tsx` and add the corresponding test command to `package.json`.

## Commit & Pull Request Guidelines

Git history is not included in this checkout, so no repository-specific commit convention can be inferred. Use concise, imperative subjects such as `Add dashboard navigation` and keep each commit focused. Pull requests should explain the change, list validation performed, link relevant issues, and include screenshots or recordings for visible UI changes. Call out new dependencies, configuration changes, or known follow-up work.

## Security & Configuration

Do not commit secrets or local environment files. Expose browser-safe variables only through Vite’s `VITE_` prefix, document required values, and keep sensitive credentials on the server side.
