# syntax=docker/dockerfile:1.6

FROM node:20-bookworm-slim AS base
WORKDIR /usr/src/app

FROM base AS deps
# Copy workspace manifests to leverage npm's workspaces resolver during install
COPY package.json ./
COPY apps/backend/package.json ./apps/backend/package.json
COPY packages/shared/package.json ./packages/shared/package.json
RUN npm install

FROM deps AS build
COPY . .
RUN npm run build --workspace packages/shared \
  && npm run build --workspace apps/backend

FROM deps AS production-deps
RUN npm prune --omit=dev \
  && npm install prisma --no-save

FROM node:20-bookworm-slim AS runner
WORKDIR /usr/src/app
ENV NODE_ENV=production
ARG APP_VERSION=0.0.0
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.title="Covenant Connect Backend"
LABEL org.opencontainers.image.version="${APP_VERSION}"

COPY --from=production-deps /usr/src/app/node_modules ./node_modules
COPY --from=build /usr/src/app/package.json ./package.json
COPY --from=build /usr/src/app/apps/backend/package.json ./apps/backend/package.json
COPY --from=build /usr/src/app/apps/backend/dist ./apps/backend/dist
COPY --from=build /usr/src/app/apps/backend/prisma ./apps/backend/prisma
COPY --from=build /usr/src/app/packages/shared/package.json ./packages/shared/package.json
COPY --from=build /usr/src/app/packages/shared/dist ./packages/shared/dist

EXPOSE 8000
CMD ["sh", "-c", "npx prisma migrate deploy && node apps/backend/dist/main.js"]
