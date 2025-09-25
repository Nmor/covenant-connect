# syntax=docker/dockerfile:1.6

FROM node:20-bookworm-slim AS base
WORKDIR /usr/src/app

FROM base AS deps
COPY package.json ./
COPY apps/frontend/package.json ./apps/frontend/package.json
COPY packages/shared/package.json ./packages/shared/package.json
COPY scripts/postinstall.js ./scripts/postinstall.js
RUN npm install

FROM deps AS build
COPY . .
RUN npm run build --workspace packages/shared \
  && npm run build --workspace apps/frontend

FROM deps AS production-deps
RUN npm prune --omit=dev

FROM node:20-bookworm-slim AS runner
WORKDIR /usr/src/app
ENV NODE_ENV=production
ENV PORT=3000
ARG APP_VERSION=0.0.0
ENV APP_VERSION=${APP_VERSION}
ENV NEXT_TELEMETRY_DISABLED=1
LABEL org.opencontainers.image.title="Covenant Connect Frontend"
LABEL org.opencontainers.image.version="${APP_VERSION}"

COPY --from=production-deps /usr/src/app/node_modules ./node_modules
COPY --from=build /usr/src/app/package.json ./package.json
COPY --from=build /usr/src/app/apps/frontend/package.json ./apps/frontend/package.json
COPY --from=build /usr/src/app/apps/frontend/next.config.js ./apps/frontend/next.config.js
COPY --from=build /usr/src/app/apps/frontend/public ./apps/frontend/public
COPY --from=build /usr/src/app/apps/frontend/.next ./apps/frontend/.next
COPY --from=build /usr/src/app/packages/shared/package.json ./packages/shared/package.json
COPY --from=build /usr/src/app/packages/shared/dist ./packages/shared/dist

EXPOSE 3000
CMD ["sh", "-c", "node apps/frontend/node_modules/next/dist/bin/next start -p ${PORT:-3000}"]
