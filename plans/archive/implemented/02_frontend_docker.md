# 02 — Frontend Dockerfile (React + nginx)

## Location

`frontend/Dockerfile`

## Dockerfile Plan

```dockerfile
# ── Build stage ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --production=false

COPY . .

# API URL injected at build time
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
```

## nginx.conf

Place at `frontend/nginx.conf`:

```nginx
server {
    listen 8080;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    # SPA: fall back to index.html for client-side routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Proxy API calls to backend service (Cloud Run service-to-service)
    # In production, the frontend calls the API URL directly via VITE_API_URL,
    # so this block is mainly for local docker-compose usage.
    location /api/ {
        proxy_pass http://api:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Security headers
    add_header X-Content-Type-Options nosniff always;
    add_header X-Frame-Options DENY always;
    add_header Referrer-Policy strict-origin-when-cross-origin always;

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check for Cloud Run
    location /health {
        return 200 'ok';
        add_header Content-Type text/plain;
    }
}
```

## API URL Strategy

Vite injects environment variables at **build time**, not runtime. Two approaches:

### Option A: Build-time injection (simpler, recommended)

- Pass `--build-arg VITE_API_URL=https://focusgroups-api-xxxxx.run.app` during `docker build`.
- Frontend code uses `import.meta.env.VITE_API_URL` as the API base URL.
- Different builds for staging vs prod.

### Option B: Runtime config file (if multi-env from one image is needed)

- At container start, generate a `/usr/share/nginx/html/config.js` from env vars.
- `index.html` loads `<script src="/config.js">` which sets `window.__CONFIG__`.
- App reads `window.__CONFIG__.API_URL` instead of `import.meta.env`.
- More complex but allows one image for all environments.

**Recommendation**: Start with Option A. If we need multi-env later, switch to B.

## Frontend Code Change Required

The frontend currently uses Vite's dev proxy (`/api` → `localhost:8000`). For production:

1. Create a shared API client module (e.g. `frontend/src/api.js`):
```js
const API_BASE = import.meta.env.VITE_API_URL || '';

export function apiUrl(path) {
  return `${API_BASE}${path}`;
}
```

2. Replace all `fetch('/api/...')` calls with `fetch(apiUrl('/api/...'))`.

In dev mode, `VITE_API_URL` is empty so requests go to the Vite proxy as before. In production, they go to the full Cloud Run API URL.

## .dockerignore (frontend/)

```
node_modules/
dist/
.env
*.test.js
*.test.jsx
```

## Testing Locally

```bash
cd frontend
docker build -t fg-web --build-arg VITE_API_URL=http://localhost:8080 .
docker run --rm -p 3000:8080 fg-web

# Verify
curl http://localhost:3000/health
```

## Image Size

- node:20-alpine build stage: ~300MB (discarded)
- nginx:1.27-alpine + static assets: ~30-50MB final image
