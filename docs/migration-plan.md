# SQLAlchemy to Prisma migration and cutover plan

This runbook codifies the steps required to migrate production data off the
legacy SQLAlchemy/Flask stack and cut over to the NestJS/Prisma services that
now power Covenant Connect. It assumes the Prisma schema remains aligned with
the historic PostgreSQL tables and focuses on orchestrating a safe migration,
validating data, enabling third-party integrations, and performing the final
service swap.

## 1. Pre-migration checklist

1. **Freeze change windows**
   - Announce the migration window and place the Flask application in read-only
     mode (disable writes or schedule downtime).
2. **Capture database and secrets backups**
   - Take a full PostgreSQL base backup (`pg_dump --format=custom`) and verify it
     restores in a staging environment.
   - Export current `.env` secrets so OAuth, payments, and queue credentials can
     be referenced when populating the new environment.
3. **Provision staging environments**
   - Stand up staging copies of PostgreSQL and Redis using the Helm chart or the
     Docker Compose stack so smoke tests can be rehearsed ahead of the production
     cutover.

## 2. Database schema migration

1. **Snapshot the live schema**
   - Use Prisma's diff tooling to capture a baseline migration against the
     existing SQLAlchemy-managed schema:

     ```bash
     # Point DATABASE_URL at a readonly replica or a production clone
     pnpm --filter @covenant-connect/backend prisma migrate diff \
       --from-url "$DATABASE_URL" \
       --to-schema-datamodel apps/backend/prisma/schema.prisma \
       --script > prisma-migration.sql
     ```

   - Review the generated SQL to confirm only Prisma metadata tables are added
     (e.g. `_prisma_migrations`).
2. **Create the initial Prisma migration**
   - Apply the diff to a staging database and capture it as the "init" migration
     if it has not already been committed (`20250922022205_init`).
3. **Replay historical migrations**
   - Ensure any follow-up migrations (integration settings, email providers,
     church profile extensions) are present in `apps/backend/prisma/migrations`
     and run `pnpm --filter @covenant-connect/backend prisma migrate deploy` in
     staging until Prisma reports the database is up to date.
4. **Validate data parity**
   - Run aggregate comparisons between the Python ORM and Prisma:
     - Row counts per table (`SELECT count(*) FROM users;` etc.).
     - Spot-check high-value entities (members, donations, events).
   - Use Prisma scripts to sanity-check the data once connected to staging.

## 3. Production migration execution

1. **Schedule downtime** (if zero-downtime dual writes are unavailable) and take
   a fresh PostgreSQL snapshot immediately before applying migrations.
2. **Run migrations**

   ```bash
   # With DATABASE_URL pointed at production and SHADOW_DATABASE_URL unset
   pnpm --filter @covenant-connect/backend prisma migrate deploy
   ```

   - Prisma will create the `_prisma_migrations` table and mark historical steps
     as applied without mutating existing records.
3. **Warm Prisma client caches**
   - Run `pnpm --filter @covenant-connect/backend prisma:generate` so the latest
     Prisma client is baked into the backend image.
4. **Smoke tests**
   - Hit `/health/ready` on the Nest API and load key queries (accounts,
     donations, events, prayer) to confirm data resolves via Prisma.

## 4. Third-party integration enablement

1. **OAuth providers**
   - Populate `GOOGLE_*`, `FACEBOOK_*`, and `APPLE_*` secrets so the Nest
     `GoogleOAuthProvider`, `FacebookOAuthProvider`, and `AppleOAuthProvider` can
     issue authorization URLs and exchange tokens.【F:apps/backend/src/modules/auth/auth.module.ts†L6-L32】【F:apps/backend/src/modules/auth/providers/google.provider.ts†L1-L111】
   - Use staging to walk through end-to-end sign-ins, verifying new `AccountProvider`
     rows appear in Prisma.
2. **Payment gateways**
   - Configure Stripe, Paystack, Fincra, and Flutterwave keys in the backend
     secret. Each provider implements the shared payment interface and calls the
     live APIs for initialization, verification, and refunds.【F:apps/backend/src/modules/donations/donations.module.ts†L1-L39】【F:apps/backend/src/modules/donations/providers/stripe.provider.ts†L1-L101】
   - Run provider-specific smoke tests (test cards, sandbox references) before
     pointing production webhooks at the Nest API (`/donations/providers/*`).
3. **Queues and automation**
   - Ensure Redis connectivity (`REDIS_URL`) is available so the `TasksService`
     can create BullMQ queues with retry and repeat schedules.【F:apps/backend/src/modules/tasks/tasks.service.ts†L1-L158】
   - Start the worker entry point (`node dist/src/task-worker.main.js`) alongside
     the API to process prayer notifications, KPI digests, and automation jobs.【F:apps/backend/src/modules/tasks/tasks.module.ts†L1-L24】

## 5. Cutover from Python services

1. **Deploy the Node services**
   - Build and publish the backend/frontend Docker images via CI, then deploy
     them with `deploy/helm` using production values for secrets, image tags, and
     ingress settings.【F:docs/deployment-runbook.md†L1-L118】
2. **Dual-run verification**
   - Keep the Flask application online in read-only mode while directing a pilot
     slice of traffic (internal staff) to the Next.js UI and Nest API.
   - Monitor logs, queue throughput, and payment provider dashboards for parity
     issues.
3. **Switch primary traffic**
   - Update DNS, load balancer rules, or ingress routes so all user traffic hits
     the Node services.
   - Remove read-only restrictions once the new stack is fully serving writes.
4. **Decommission Python stack**
   - After a stability window, archive the Flask containers and revoke unused
     secrets. Keep snapshots for rollback until the migration is declared
     complete.

## 6. Rollback strategy

- If Prisma migrations introduce issues, stop the Nest services and restore the
  pre-migration PostgreSQL snapshot. Because Prisma only adds metadata tables,
  restoration is a straightforward database rollback.
- Re-enable the Flask application in read/write mode and communicate the delay.
- Address root causes in staging before re-attempting the migration.

## 7. Post-cutover tasks

- Update monitoring dashboards and alerts to point at the Nest API and BullMQ
  worker metrics.
- Transfer ownership of OAuth/webhook endpoints with the respective providers so
  future rotations do not reference the Python hosts.
- Schedule a follow-up retrospective to capture lessons learned and validate that
  all admin workflows now run against the Node services (`apps/frontend/app/admin/*`).
