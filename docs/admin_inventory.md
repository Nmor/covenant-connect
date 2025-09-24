# Admin experience inventory

With the Flask blueprints removed, the admin experience now ships entirely from
the TypeScript stack. This document tracks the surfaces that exist today and the
areas that still need parity work as we expand the Nest/Next implementation.

## Current surfaces

- **Executive dashboard (`apps/frontend/app/dashboard/page.tsx`)** – provides the
  high-level health view backed by the `reports` module in the API. Donation,
  event, and prayer metrics now pull directly from Prisma via the Nest services
  ported in this migration.
- **Care follow-up (`apps/frontend/app/admin/care/page.tsx`)** – renders recent
  pastoral interactions and will pick up inline editing once the corresponding
  Prisma mutations land. The view consumes shared types exported from
  `packages/shared` and the `care` helpers in `apps/frontend/app/lib`.
- **Donations, events, accounts** – front-end components under
  `apps/frontend/app/admin` read from the new Prisma-backed endpoints exposed by
  the Nest modules (`donations.controller.ts`, `events.controller.ts`,
  `auth/accounts` service), providing the same data the Flask templates used to
  surface.

## Parity gaps

- **Member profile editing** – read-only views exist but the mutation endpoints
  for updating assimilation stages and milestones are still on the roadmap.
- **Automation tooling** – the BullMQ worker boots successfully via the new
  `task-worker.main.ts` entry point, but the admin UI still needs controls for
  triggering automations manually.
- **File management** – media uploads currently rely on local storage; the
  Next.js admin experience will add S3-backed uploads once the storage driver
  abstraction grows a dedicated API route.

## Historical context

The removed Flask blueprints and Jinja templates captured desired workflows for
member care, volunteer scheduling, and reporting. Those files can be referenced
via Git history if designers need to review legacy interactions, but the active
roadmap focuses on the NestJS controllers and Next.js routes now living in this
monorepo.
