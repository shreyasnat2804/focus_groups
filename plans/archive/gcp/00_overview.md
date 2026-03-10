# Dockerization & GCP Migration — Overview

## Current State

| Component | How it runs today | Target |
|-----------|-------------------|--------|
| Postgres + pgvector | Local Docker (`docker-compose.yml`, single `db` service) | Cloud SQL for Postgres 16 |
| FastAPI backend | `uvicorn focus_groups.api:app --reload` locally | Cloud Run (containerized) |
| React frontend | `npm run dev` (Vite dev server) | Cloud Run (nginx serving static build) |
| Secrets (.env) | Flat `.env` file with plaintext keys | GCP Secret Manager |
| CI/CD | None | Cloud Build or GitHub Actions → Artifact Registry → Cloud Run |

## Plan Files

| File | Scope |
|------|-------|
| `01_backend_docker.md` | Dockerfile for FastAPI, gunicorn config, health checks |
| `02_frontend_docker.md` | Multi-stage Dockerfile for React (build + nginx) |
| `03_database.md` | Cloud SQL provisioning, migrations, connection patterns |
| `04_secrets_and_config.md` | Secret Manager, env vars, service account IAM |
| `05_cloud_run.md` | Deploy config for both services, networking, domains |
| `06_ci_cd.md` | Cloud Build / GitHub Actions pipeline, Artifact Registry |
| `07_docker_compose_dev.md` | Unified local docker-compose for all services |
| `08_migration_checklist.md` | Ordered steps to execute the migration |

## Architecture After Migration

```
                    ┌──────────────────┐
                    │  Cloud DNS /     │
                    │  Load Balancer   │
                    └───────┬──────────┘
                            │
              ┌─────────────┼─────────────┐
              │                           │
    ┌─────────▼─────────┐    ┌────────────▼───────────┐
    │  Cloud Run:        │    │  Cloud Run:             │
    │  focusgroups-web   │    │  focusgroups-api        │
    │  (nginx + React)   │    │  (gunicorn + FastAPI)   │
    │  Port 8080         │    │  Port 8080              │
    └────────────────────┘    └────────────┬────────────┘
                                           │ Unix socket
                              ┌────────────▼────────────┐
                              │  Cloud SQL Proxy         │
                              │  (sidecar / built-in)    │
                              └────────────┬─────────────┘
                                           │
                              ┌─────────────▼────────────┐
                              │  Cloud SQL                │
                              │  Postgres 16 + pgvector   │
                              └──────────────────────────┘

    Secrets: GCP Secret Manager → mounted as env vars on Cloud Run
    Images:  Artifact Registry (us-central1-docker.pkg.dev)
    Storage: Cloud Storage (model checkpoints, exports)
```

## Guiding Principles

1. **Containers must be identical in dev and prod** — same Dockerfile, different env vars.
2. **No secrets baked into images** — everything via Secret Manager or env vars at deploy time.
3. **Cloud Run port 8080** — both services listen on `$PORT` (defaults to 8080).
4. **Health checks first** — `/health` (liveness) and `/ready` (readiness) already exist.
5. **One concern per container** — backend and frontend are separate services.
6. **Local dev still works** — `docker compose up` runs everything locally with no GCP dependency.
