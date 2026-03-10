# Deploy to Render — Plan

## Goal

Get a public URL a friend can visit. No server management, minimal cost.

## Architecture on Render

```
  Friend's browser
       │
       ▼
  ┌─────────────┐     VITE_API_URL      ┌─────────────┐
  │  fg-web      │ ───────────────────▶  │  fg-api      │
  │  (nginx +    │                       │  (gunicorn + │
  │   React)     │                       │   FastAPI)   │
  │  free / $7   │                       │  free / $7   │
  └─────────────┘                       └──────┬──────┘
                                               │ DATABASE_URL
                                        ┌──────▼──────┐
                                        │  fg-db       │
                                        │  Postgres 16 │
                                        │  + pgvector  │
                                        │  free / $7   │
                                        └─────────────┘
```

## Free Tier Limitations

| Limit | Impact |
|-------|--------|
| Services spin down after 15 min idle | ~1 min cold start when friend visits |
| Free DB expires after 30 days | Demo stops working; must upgrade or recreate |
| 1 GB database storage | Fine for demo data |
| 750 free instance hours/mo | Enough for two services |

**Recommendation**: Free tier is fine for a demo. If cold starts annoy your friend, Starter ($7/service/mo = ~$21 total) keeps things warm.

## Code Changes Needed

### 1. Backend: Support DATABASE_URL (Render provides this)

`db.py` currently reads individual `PG_HOST`, `PG_PORT`, etc. env vars. Render gives a single `DATABASE_URL` connection string. Add a fallback:

```python
def _pg_kwargs() -> dict:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"dsn": database_url}
    return {
        "host": os.getenv("PG_HOST", "localhost"),
        "port": os.getenv("PG_PORT", "5432"),
        "dbname": os.getenv("PG_DB", "focusgroups"),
        "user": os.getenv("PG_USER", "fg_user"),
        "password": os.getenv("PG_PASSWORD", "localdev"),
    }
```

No other code changes. `psycopg2.connect(dsn=...)` accepts a connection string natively.

### 2. Frontend: VITE_API_URL build arg

Already implemented — `apiUrl()` in `api.js` reads `VITE_API_URL`. Render sets this at build time via the render.yaml `envVars`.

### 3. CORS: Add Render frontend URL

Backend needs `CORS_ORIGINS` to include the Render frontend URL. Set via env var — no code change.

### 4. Nginx: Listen on $PORT

Render requires services to listen on the port specified by `$PORT` env var (defaults to 10000). Current nginx.conf hardcodes 8080. Two options:

**Option A** (simple): Use `EXPOSE 10000` and hardcode 10000 in nginx.conf for Render.
**Option B** (flexible): Use envsubst in Dockerfile CMD to template the port.

Recommendation: Option B — keep 8080 as default, override with $PORT on Render.

### 5. DB Schema Init

Render Postgres doesn't auto-run init.sql. Options:
- **render.yaml `preDeployCommand`**: Run `psql $DATABASE_URL -f db/init.sql` before each deploy
- Or init on first API startup

Recommendation: preDeployCommand — it's explicit and runs migrations too.

## render.yaml (Blueprint)

```yaml
databases:
  - name: fg-db
    plan: free
    databaseName: focusgroups
    user: fg_user
    postgresMajorVersion: "16"

services:
  - type: web
    name: fg-api
    runtime: docker
    plan: free
    region: oregon
    dockerfilePath: ./Dockerfile
    healthCheckPath: /health
    preDeployCommand: "psql $DATABASE_URL -f db/init.sql && bash db/migrate.sh"
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: fg-db
          property: connectionString
      - key: ANTHROPIC_API_KEY
        sync: false  # manually set in Render dashboard
      - key: CORS_ORIGINS
        fromService:
          name: fg-web
          type: web
          property: host
      - key: PORT
        value: "8080"

  - type: web
    name: fg-web
    runtime: docker
    plan: free
    region: oregon
    dockerfilePath: ./frontend/Dockerfile
    healthCheckPath: /health
    envVars:
      - key: VITE_API_URL
        fromService:
          name: fg-api
          type: web
          envVarKey: RENDER_EXTERNAL_URL
      - key: PORT
        value: "8080"
```

## Implementation Steps

### Step 1: Code changes
- [ ] Update `db.py` to support `DATABASE_URL`
- [ ] Update nginx.conf / frontend Dockerfile to respect `$PORT`
- [ ] Update `CORS_ORIGINS` handling to prefix `https://` to Render host
- [ ] Add `render.yaml` to repo root
- [ ] Write tests for DATABASE_URL support and PORT flexibility

### Step 2: Deploy
- [ ] Push code to `main` (or connect `poc` branch in Render dashboard)
- [ ] Go to render.com → New → Blueprint → connect GitHub repo
- [ ] Render reads `render.yaml`, creates DB + 2 services
- [ ] Set `ANTHROPIC_API_KEY` manually in Render dashboard (secret)
- [ ] Wait for first deploy (~5 min)
- [ ] Hit the frontend URL — send it to your friend

### Step 3: Init pgvector
After first deploy, run in Render's Shell tab or via psql:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```
(Or add to `db/init.sql` which runs via preDeployCommand)

pgvector is already in `init.sql` line 1, so the preDeployCommand handles this automatically.

## Cost Summary

| Plan | API | Web | DB | Total |
|------|-----|-----|----|-------|
| Free | $0 | $0 | $0 | **$0** (30-day DB limit) |
| Starter | $7 | $7 | $7 | **$21/mo** (no limits) |
