# Covenant Connect

Covenant Connect is a monorepo that powers the ministry management platform with
a fully type-safe stack. The NestJS API, Next.js frontend, and shared domain
package live side-by-side so features ship with consistent contracts from the
UI down to the database.

## Project layout

```
.
├── apps
│   ├── backend   # NestJS API (Prisma, BullMQ, Swagger)
│   └── frontend  # Next.js 13 App Router experience
├── packages
│   └── shared    # Generated Prisma types + shared domain helpers
├── deploy        # Helm chart + ECS task definitions for the Node services
└── docs          # Architecture and operational runbooks
```

* `apps/backend` exposes modules for accounts, churches, donations, events,
  prayer, content, integrations, reporting, and task orchestration. Everything
  persists through Prisma models so the API can run against PostgreSQL with
  migration enforcement at startup.
* `apps/frontend` renders the public marketing site and authenticated dashboard.
  It consumes the shared TypeScript contracts and targets the same API used by
  partner integrations.
* `packages/shared` publishes the generated Prisma client typings together with
  friendly aliases such as `UserAccount`, `Donation`, and the string-id `Church`
  interface consumed by both apps.

Need to surface event and sermon listings on a WordPress site? Install the
plugin under `integrations/wordpress-plugin`, point it at the API, and embed the
provided shortcodes.

## Getting started

1. Install dependencies and generate the Prisma client:

   ```bash
   pnpm install
   pnpm run prisma:generate
   ```

2. Provide a PostgreSQL connection string:

   ```bash
   export DATABASE_URL="postgresql://user:password@localhost:5432/covenant_connect"
   ```

3. Start the backend in watch mode:

   ```bash
   pnpm --filter @covenant-connect/backend dev
   ```

4. (Optional) Start the Next.js frontend:

   ```bash
   pnpm --filter @covenant-connect/frontend dev
   ```

A Docker Compose configuration lives at `docker-compose.yml` for end-to-end
local runs with PostgreSQL and Redis pre-wired. Run `docker compose up --build`
to exercise the entire stack in containers.

## Scripts

The workspace root exposes convenience scripts that fan out to each package:

* `pnpm run build` &mdash; build the shared package, backend, and frontend.
* `pnpm run lint` / `pnpm run typecheck` / `pnpm run test` &mdash; quality gates for
  every workspace.
* `pnpm --filter @covenant-connect/backend generate:openapi` &mdash; regenerate the
  OpenAPI document after making controller or DTO changes.

The backend build produces `dist/src/main.js` for the HTTP API and
`dist/src/task-worker.main.js` for BullMQ workers. Both entry points are shipped
in the production container image.

## Configuration highlights

Backend configuration is sourced from environment variables and strongly typed
configuration factories. Important values include:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string for Prisma. |
| `REDIS_URL` | Redis connection string when using the BullMQ queue driver. |
| `SESSION_SECRET` | Session encryption key. |
| `QUEUE_DRIVER` | Either `redis` or `memory` (development only). |
| `CORS_ORIGINS` | Comma separated list of allowed origins. |
| `STRIPE_*`, `PAYSTACK_*`, `FINCRA_*`, `FLUTTERWAVE_*` | Payment gateway secrets. |
| `GOOGLE_*`, `FACEBOOK_*`, `APPLE_*` | OAuth credentials for social sign-in. |

See [`docs/deployment-runbook.md`](docs/deployment-runbook.md) for detailed
production configuration, container build information, and Helm chart usage.

## Testing

Run the full backend test suite with:

```bash
pnpm --filter @covenant-connect/backend test
```

Vitest/Jest specs cover Prisma-backed services (accounts, donations, events,
churches, etc.), email providers, OAuth flows, and queue orchestration so the
TypeScript stack maintains the parity previously provided by the Flask
implementation.
