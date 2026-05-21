FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1

# Next.js bake les NEXT_PUBLIC_* dans le bundle au moment du `npm run build`.
# Il faut donc les passer comme ARG, puis les exposer en ENV avant le build,
# sinon les bundles côté navigateur contiendraient les defaults du code source
# (par ex. http://localhost:8000) au lieu des vraies URLs de production.
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_WS_URL
ARG NEXT_PUBLIC_PUBLIC_HOST
ARG NEXT_PUBLIC_ADMIN_HOST
ARG NEXT_PUBLIC_PORTAL_NAME
ARG NEXT_PUBLIC_PORTAL_NAME_PUBLIC
ARG NEXT_PUBLIC_PORTAL_NAME_ADMIN
ARG NEXT_PUBLIC_PORTAL_TAGLINE
ARG NEXT_PUBLIC_INHP_PHONES
ARG NEXT_PUBLIC_SAMU
ARG NEXT_PUBLIC_ALLO_SANTE
ARG NEXT_PUBLIC_SECOURS

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_WS_URL=${NEXT_PUBLIC_WS_URL}
ENV NEXT_PUBLIC_PUBLIC_HOST=${NEXT_PUBLIC_PUBLIC_HOST}
ENV NEXT_PUBLIC_ADMIN_HOST=${NEXT_PUBLIC_ADMIN_HOST}
ENV NEXT_PUBLIC_PORTAL_NAME=${NEXT_PUBLIC_PORTAL_NAME}
ENV NEXT_PUBLIC_PORTAL_NAME_PUBLIC=${NEXT_PUBLIC_PORTAL_NAME_PUBLIC}
ENV NEXT_PUBLIC_PORTAL_NAME_ADMIN=${NEXT_PUBLIC_PORTAL_NAME_ADMIN}
ENV NEXT_PUBLIC_PORTAL_TAGLINE=${NEXT_PUBLIC_PORTAL_TAGLINE}
ENV NEXT_PUBLIC_INHP_PHONES=${NEXT_PUBLIC_INHP_PHONES}
ENV NEXT_PUBLIC_SAMU=${NEXT_PUBLIC_SAMU}
ENV NEXT_PUBLIC_ALLO_SANTE=${NEXT_PUBLIC_ALLO_SANTE}
ENV NEXT_PUBLIC_SECOURS=${NEXT_PUBLIC_SECOURS}

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
USER nextjs
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
