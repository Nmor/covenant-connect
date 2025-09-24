# Covenant Connect Deployment Runbook

This runbook describes how the TypeScript/Nest/Next rewrite of Covenant Connect is packaged, orchestrated locally, and deployed to Kubernetes. It replaces the legacy ECS/Flask notes and focuses on the new container images, Helm chart, secrets, and CI automation that keep production reproducible.

## Container images

Two production images live under `apps/backend` and `apps/frontend` respectively. Each Dockerfile uses a multi-stage build so that the published layers only contain the compiled application and runtime dependencies.

### Backend API (`apps/backend/Dockerfile`)

* **Base image:** `node:20-bookworm-slim`
* **Build process:** installs workspace dependencies, compiles `packages/shared`, compiles the NestJS source, prunes dev dependencies, and keeps the Prisma CLI so migrations can run at start-up.
* **Entrypoint:** `npx prisma migrate deploy && node apps/backend/dist/main.js`
* **Exposed port:** `8000`
* **Build arguments:**
  * `APP_VERSION` &mdash; optional string that is baked into the image metadata and exported as `APP_VERSION` inside the container. Set this to the Git SHA or semantic version when building release artifacts.
* **Key environment variables:**

| Variable | Description | Default |
| --- | --- | --- |
| `APP_NAME` | Human friendly name used in logs. | `Covenant Connect` |
| `APP_VERSION` | Propagated from the `APP_VERSION` build arg for observability. | `0.0.0` inside the Dockerfile |
| `NODE_ENV` | Node runtime mode. | `production` |
| `PORT` | HTTP listener for the Nest API. | `8000` |
| `DATABASE_URL` | Prisma connection string (PostgreSQL). Secrets-managed in Helm. | Computed from the bundled PostgreSQL release values |
| `SHADOW_DATABASE_URL` | Optional Prisma shadow database for migrations. | empty |
| `REDIS_URL` | Redis connection string for queues and caching. | Computed from Redis release values |
| `SESSION_SECRET` | Encryption secret for cookie/session signing. | _required_ |
| `SESSION_TTL` | TTL in seconds for session cookies. | `604800` |
| `QUEUE_DRIVER` | Either `redis` or `memory`. Use `redis` in production. | `redis` in docker-compose and values |
| `QUEUE_MAX_ATTEMPTS` | Default BullMQ retry attempts. | `3` |
| `CORS_ORIGINS` | Comma separated list of allowed CORS origins. | `http://localhost:3000` in dev, production override via Helm |
| `COOKIE_DOMAIN` / `COOKIE_SECURE` | Hardens session cookie scope. | empty / `true` |
| `ASSET_BASE_URL` | Optional CDN origin for uploaded assets. | empty |
| `STORAGE_DRIVER` | `local` or `s3` driver for file uploads. | `local` |
| `LOCAL_STORAGE_DIR` | Local uploads directory when using the `local` driver. | `/tmp/uploads` in docker-compose |
| `AWS_*` variables | Required only when `STORAGE_DRIVER=s3`. | empty |
| Payment secrets (`STRIPE_*`, `PAYSTACK_*`, `FINCRA_*`, `FLUTTERWAVE_*`) | Provider API keys and webhook secrets. | empty |
| OAuth secrets (`GOOGLE_*`, `FACEBOOK_*`, `APPLE_*`) | Third-party sign-on credentials. | empty |
| `KPI_DIGEST_CRON`, `FOLLOW_UP_CRON` | Cron schedules for background jobs. | `0 7 * * 1` / `0 */6 * * *` |

The Helm chart injects secrets through `deploy/helm/templates/backend-secret.yaml`, while the local compose file passes development-safe defaults from `docker-compose.yml`.

### Frontend (`apps/frontend/Dockerfile`)

* **Base image:** `node:20-bookworm-slim`
* **Build process:** installs workspace dependencies, compiles `packages/shared`, runs `next build`, and prunes dev dependencies.
* **Entrypoint:** `node apps/frontend/node_modules/next/dist/bin/next start -p ${PORT}`
* **Exposed port:** `3000`
* **Build arguments:**
  * `APP_VERSION` &mdash; same semantics as the backend image.
* **Key environment variables:**

| Variable | Description | Default |
| --- | --- | --- |
| `APP_VERSION` | Propagated from the build arg for traceability. | `0.0.0` |
| `NODE_ENV` | Next.js runtime mode. | `production` |
| `PORT` | HTTP listener for the Next.js server. | `3000` |
| `NEXT_PUBLIC_API_BASE_URL` | Public API origin embedded in the browser bundle. Use the internal service DNS (e.g. `http://covenant-connect-backend:8000`) when running in Kubernetes. | `http://localhost:8000` when unset |

## Local orchestration with Docker Compose

`docker-compose.yml` wires the application containers together with PostgreSQL and Redis for end-to-end smoke testing on a workstation. The compose definition builds both Dockerfiles (injecting `APP_VERSION=local`), provisions `postgres:15-alpine` and `redis:7.2-alpine`, configures health checks, publishes ports `3000` and `8000` for the UI and API, and runs the BullMQ worker so background tasks execute locally.【F:docker-compose.yml†L1-L100】

Run the stack locally with:

```bash
docker compose up --build
```

The backend container runs `prisma migrate deploy` on start-up so the fresh PostgreSQL instance is seeded automatically. Data volumes (`postgres-data`, `redis-data`) persist database state between restarts, and environment variables mirror the production configuration while remaining safe for development.

## Kubernetes deployment with Helm

The `deploy/helm` chart provisions the full runtime in a single release. Installing the chart creates:

* A backend `Deployment` and `Service` that run the Nest API and expose health probes on `/health/live` and `/health/ready`; the readiness probe now checks Prisma migrations and Redis connectivity before serving traffic.【F:deploy/helm/templates/backend-deployment.yaml†L1-L45】【F:deploy/helm/templates/backend-service.yaml†L1-L15】【F:apps/backend/src/modules/health/health.indicator.ts†L1-L138】
* A dedicated worker `Deployment` that launches `node dist/src/task-worker.main.js` so BullMQ jobs stay online when the Python services are decommissioned.【F:deploy/helm/templates/worker-deployment.yaml†L1-L48】
* A frontend `Deployment`, `Service`, and optional `Ingress` for the Next.js UI.【F:deploy/helm/templates/frontend-deployment.yaml†L1-L42】【F:deploy/helm/templates/frontend-service.yaml†L1-L15】【F:deploy/helm/templates/frontend-ingress.yaml†L1-L24】
* Stateful Redis and PostgreSQL workloads backed by persistent volume claims, plus dedicated secrets for their credentials.【F:deploy/helm/templates/redis-statefulset.yaml†L1-L40】【F:deploy/helm/templates/postgres-statefulset.yaml†L1-L43】【F:deploy/helm/templates/redis-secret.yaml†L1-L9】【F:deploy/helm/templates/postgres-secret.yaml†L1-L11】
* A backend environment secret that captures all required application secrets and non-secret overrides.【F:deploy/helm/templates/backend-secret.yaml†L1-L33】

### Required values

Override the following values when deploying to a cluster:

* `backend.image.repository` and `backend.image.tag` &mdash; point to the published GHCR image for the API.
* `frontend.image.repository` and `frontend.image.tag` &mdash; point to the published GHCR image for the UI.
* `backend.secretEnv.SESSION_SECRET` &mdash; at least 32 bytes of entropy.
* `backend.secretEnv.DATABASE_URL` / `backend.secretEnv.REDIS_URL` if you are using managed services instead of the bundled StatefulSets.
* `postgres.auth.password` &mdash; production-grade password; update the matching Helm secret when rotated.
* `redis.auth.enabled=true` and `redis.auth.password` when Redis requires authentication.
* Any payment or OAuth secrets that must be available to the API.

### Installation

Use the sample below as a starting point for production:

```bash
helm upgrade --install covenant-connect deploy/helm \
  --set backend.image.repository=ghcr.io/<org>/covenant-connect/backend \
  --set backend.image.tag=<git-sha> \
  --set frontend.image.repository=ghcr.io/<org>/covenant-connect/frontend \
  --set frontend.image.tag=<git-sha> \
  --set backend.secretEnv.SESSION_SECRET=$(openssl rand -hex 32) \
  --set postgres.auth.password=<postgres-password> \
  --set backend.secretEnv.STRIPE_SECRET_KEY=<stripe-secret> \
  --values deploy/helm/values.yaml
```

When deploying behind an ingress controller, enable and customise `ingress.*` in `values.yaml` so traffic reaches the frontend service. The default values file also exposes knobs for replica counts, resource requests, persistent volume sizes, and image pull secrets.【F:deploy/helm/values.yaml†L1-L84】

## Continuous integration and image publishing

`.github/workflows/ci.yml` contains two jobs:

1. **`quality`** (existing) &mdash; installs dependencies, lints, type-checks, and runs tests across all workspaces.
2. **`docker-images`** &mdash; uses Docker Buildx to build both production images, tags them as `ghcr.io/<repo>/backend` and `ghcr.io/<repo>/frontend`, and pushes `latest` + SHA tags on merges to `main`. Pull requests build the images for validation without publishing. Authentication happens via the built-in `GITHUB_TOKEN` with `packages: write` permission.【F:.github/workflows/ci.yml†L1-L73】

The build step passes `APP_VERSION=${{ github.sha }}` so the resulting containers advertise the exact commit that produced them, aligning with the documentation above.【F:.github/workflows/ci.yml†L45-L72】

## Release checklist

1. Land application changes on `main`; CI will lint, test, and publish fresh backend/frontend images to GHCR.
2. Promote the images in Kubernetes by running `helm upgrade` with the new tags (or configure Flux/Argo to watch GHCR tags).
3. Update any rotated secrets via `helm upgrade --set backend.secretEnv.*=...` so they are re-materialised in the backing `Secret` resources.
4. Verify health probes (`/health/live`, `/health/ready`) and Next.js status via `kubectl get pods` and `kubectl port-forward` as needed.

## Troubleshooting tips

* If the API pods crash on start-up, inspect the Prisma migration logs printed by the container entrypoint. Missing `DATABASE_URL` or incorrect credentials are the common causes.
* Frontend pods returning 502s usually indicate `NEXT_PUBLIC_API_BASE_URL` pointing to an unreachable hostname; ensure it targets the internal backend service when running inside the cluster.
* Redis or PostgreSQL PVC provisioning failures can be resolved by setting `redis.persistence.storageClassName` and `postgres.persistence.storageClassName` to a class supported by the cluster.
