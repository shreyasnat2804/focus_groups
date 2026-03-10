# 07 — Local Development Docker Compose

## Goal

Replace the current single-service `docker-compose.yml` (DB only) with a full local stack: DB + API + Frontend. Developers can run `docker compose up` and have everything working.

## Updated `docker-compose.yml`

```yaml
services:
  db:
    image: pgvector/pgvector:pg16
    container_name: fg_postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-fg_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-localdev}
      POSTGRES_DB: ${POSTGRES_DB:-focusgroups}
    ports:
      - "5432:5432"
    volumes:
      - pg_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fg_user -d focusgroups"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: fg_api
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      PG_HOST: db
      PG_PORT: 5432
      PG_DB: ${POSTGRES_DB:-focusgroups}
      PG_USER: ${POSTGRES_USER:-fg_user}
      PG_PASSWORD: ${POSTGRES_PASSWORD:-localdev}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      CORS_ORIGINS: "http://localhost:5173,http://localhost:3000,http://localhost:8080"
      LOG_FORMAT: text
      LOG_LEVEL: DEBUG
    ports:
      - "8000:8080"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  web:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_URL: ""  # empty = use nginx proxy to api service
    container_name: fg_web
    restart: unless-stopped
    depends_on:
      api:
        condition: service_healthy
    ports:
      - "3000:8080"

volumes:
  pg_data:
```

## How It Works

1. **DB** starts first, runs `init.sql`, waits until healthy.
2. **API** starts after DB is healthy. Connects to `db:5432` (Docker DNS).
3. **Web** starts after API is healthy. nginx proxies `/api/` to `api:8080`.

## Port Mapping

| Service | Container Port | Host Port | URL |
|---------|---------------|-----------|-----|
| db | 5432 | 5432 | `localhost:5432` |
| api | 8080 | 8000 | `http://localhost:8000` |
| web | 8080 | 3000 | `http://localhost:3000` |

## Development Workflow Options

### Full stack (all containers)
```bash
docker compose up --build
```

### DB only (run API/frontend natively for hot reload)
```bash
docker compose up db
# Then in separate terminals:
uvicorn focus_groups.api:app --reload --port 8000
cd frontend && npm run dev
```

This preserves the current dev experience while adding the option to test the full containerized stack.

## Changes from Current `docker-compose.yml`

| What | Before | After |
|------|--------|-------|
| Services | `db` only | `db`, `api`, `web` |
| Version key | `version: "3.9"` | Removed (deprecated in Compose V2) |
| DB healthcheck | None | `pg_isready` |
| `env_file` | `.env` | Inline with defaults |
