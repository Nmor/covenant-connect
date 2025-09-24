# Covenant Connect TypeScript Architecture

This document captures the initial structure for the JavaScript/TypeScript rewrite of Covenant Connect. It highlights the technology choices, module layout, and the plan for expanding feature parity with the Python/Flask implementation.

## Technology stack

| Area      | Selection | Rationale |
|-----------|-----------|-----------|
| Backend   | [NestJS](https://nestjs.com/) on Node 18+ | Decorator-driven modules mirror Flask blueprints, dependency injection keeps the code modular, and the ecosystem integrates well with Prisma, class-validator, and BullMQ. |
| ORM       | Prisma | Prisma offers schema-first modelling with type-safe client generation. Accounts, churches, donations, and sermons already persist through Prisma models, with the remaining services staged for migration. |
| Auth      | argon2 password hashing + pluggable OAuth handlers | Mirrors the existing local login and social sign-in flows while allowing future provider-specific strategies. |
| Queue     | BullMQ/Redis (planned) | The in-memory task queue abstracts the interface required for follow-up scheduling, making it simple to drop in BullMQ workers later. |
| Frontend  | Next.js 13 app router + Tailwind CSS | Provides hybrid SSG/SSR for marketing pages and authenticated dashboards, while Tailwind accelerates UI delivery. |
| Shared    | TypeScript workspace package | Domain types are colocated in `packages/shared` so both the backend and frontend consume a single source of truth for entities such as `UserAccount`, `Donation`, and `Event`. |

## Monorepo layout

```
.
├── package.json            # npm workspaces orchestrating backend, frontend, shared
├── tsconfig.base.json      # Compiler defaults shared across packages
├── apps
│   ├── backend             # NestJS API
│   └── frontend            # Next.js web experience
├── integrations
│   └── wordpress-plugin    # Installable WordPress plugin that consumes the API
└── packages
    └── shared              # Domain interfaces shared across the stack
```

### Backend structure

```
apps/backend
├── src
│   ├── main.ts             # Nest bootstrap, CORS, helmet
│   ├── app.module.ts       # Global module wiring
│   ├── config/             # Environment-backed configuration slices
│   └── modules/
│       ├── accounts/       # Account repository + service
│       ├── auth/           # Login, registration, social providers, session store
│       ├── churches/       # Church profile CRUD
│       ├── content/        # Sermons & homepage content APIs
│       ├── donations/      # Multi-gateway donation orchestration
│       ├── email/          # Provider management + dispatch façade
│       ├── events/         # Event planning + ICS feeds
│       ├── health/         # Terminus-powered health checks
│       ├── integrations/   # Payment/email integration settings
│       ├── prayer/         # Prayer intake & follow-up metadata
│       ├── reports/        # Aggregate KPI reporting
│       └── tasks/          # Background job queue abstraction
```

Each module exposes a Nest `Module`, `Service`, and (where relevant) `Controller`. Accounts, churches, donations, and the content module’s sermon endpoints already persist data through Prisma, while the remaining modules still use in-memory stores whose method contracts align with the Prisma models for a straightforward swap to the database.

### Frontend structure

```
apps/frontend
├── app/                    # Next.js app router routes
│   ├── layout.tsx          # Global shell + font loading
│   ├── page.tsx            # Marketing landing page with SSR data fetch
│   ├── solutions/wordpress-plugin/page.tsx  # WordPress plugin marketing experience
│   └── dashboard/page.tsx  # Staff dashboard view
├── lib/api.ts              # Thin typed fetch wrappers for backend endpoints
├── tailwind.config.ts      # Tailwind design tokens
├── postcss.config.js       # Tailwind + autoprefixer pipeline
└── app/globals.css         # Tailwind entry point + base styles
```

The marketing surface for the WordPress integration now lives in the Next.js app (`/solutions/wordpress-plugin`), replacing the Flask-rendered landing page and moving more of the public experience into the TypeScript stack.

All data fetching uses the shared API client which reads `NEXT_PUBLIC_API_BASE_URL`. When the backend is unavailable the UI falls back to placeholder content so the experience degrades gracefully during local development.

### WordPress plugin

```
integrations/wordpress-plugin
├── covenant-connect.php           # Plugin bootstrap and constants
├── includes/
│   ├── class-covenant-connect-api-client.php
│   └── class-covenant-connect-plugin.php
├── assets/style.css               # Theme-friendly frontend styles
└── README.md                      # Installation and shortcode usage guide
```

The plugin registers admin settings so site owners can point WordPress at the Covenant Connect API, then exposes `[covenant_connect_sermons]` and `[covenant_connect_events]` shortcodes that render responsive listings. Responses are cached via WordPress transients to limit API calls, and the HTML inherits theme typography so churches can drop embeds into existing pages without bespoke styling.

## Follow-up work

1. **Database schema migration** – Translate the SQLAlchemy models into Prisma schema and generate the client. Replace the in-memory repositories in `accounts`, `donations`, `events`, etc. with Prisma-backed services.
2. **OAuth provider integration** – Implement Google, Facebook, and Apple strategies using Passport or direct OAuth clients, persisting tokens and refresh workflows.
3. **Payment gateways** – Replace the mock donation lifecycle with concrete SDK integrations for Paystack, Fincra, Stripe, and Flutterwave plus webhook verification endpoints.
4. **Queue infrastructure** – Connect the tasks module to Redis-backed BullMQ workers and port scheduled jobs (KPI digests, follow-ups, automation runners).
5. **Testing & CI** – Introduce Vitest/Jest suites that mirror the Python pytest coverage and configure GitHub Actions for linting, type-checking, and tests across the monorepo.
6. **Deployment scripts** – Author Dockerfiles and Terraform/Helm manifests for the Node services, aligning with the deployment practices documented in `docs/deployment-runbook.md`.
7. **WordPress polish** – Ship Gutenberg blocks and richer templating around the new shortcodes, plus automated packaging so the plugin can be distributed through managed releases.

This scaffold provides a production-ready foundation while leaving room to iteratively port the remaining domain logic from the Flask application.
