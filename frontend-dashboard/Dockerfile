FROM node:22-slim AS build
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8080
ARG NEXT_PUBLIC_SITE_URL=http://localhost:3000
ARG NEXT_PUBLIC_ANALYST_ID=customer-support
ARG NEXT_PUBLIC_HIGH_RISK_THRESHOLD=0.75
ARG NEXT_PUBLIC_REFRESH_INTERVAL_MS=10000
ARG NEXT_PUBLIC_API_TIMEOUT_MS=5000
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_ANALYST_ID=$NEXT_PUBLIC_ANALYST_ID
ENV NEXT_PUBLIC_HIGH_RISK_THRESHOLD=$NEXT_PUBLIC_HIGH_RISK_THRESHOLD
ENV NEXT_PUBLIC_REFRESH_INTERVAL_MS=$NEXT_PUBLIC_REFRESH_INTERVAL_MS
ENV NEXT_PUBLIC_API_TIMEOUT_MS=$NEXT_PUBLIC_API_TIMEOUT_MS
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# Cloudflare workerd is linked against glibc; Debian slim provides its loader.
# Alpine (musl) reports the present executable as ENOENT at runtime.
FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --chown=node:node --from=build /app/package.json /app/package-lock.json ./
COPY --chown=node:node --from=build /app/node_modules ./node_modules
COPY --chown=node:node --from=build /app/dist ./dist
RUN chown node:node /app
USER node
EXPOSE 3000
CMD ["./node_modules/.bin/wrangler", "dev", "--config", "dist/server/wrangler.json", "--ip", "0.0.0.0", "--port", "3000"]
