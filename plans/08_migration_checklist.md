# 08 — Migration Checklist

Ordered steps to go from local-only to running on GCP. Each step is independently testable.

## Phase 1: Dockerize Locally

- [ ] **Split requirements**: Create `requirements.txt` (API only) and `requirements-ml.txt` (offline jobs). Remove `sentence-transformers` from API deps.
- [ ] **Add `gunicorn`** to `requirements.txt`.
- [ ] **Create `.dockerignore`** at project root.
- [ ] **Create backend `Dockerfile`** at project root (multi-stage, see `01_backend_docker.md`).
- [ ] **Build and test backend image locally**:
  ```bash
  docker build -t fg-api .
  docker run --rm --network host --env-file .env fg-api
  curl http://localhost:8080/health
  ```
- [ ] **Create `frontend/nginx.conf`**.
- [ ] **Create `frontend/Dockerfile`** (multi-stage, see `02_frontend_docker.md`).
- [ ] **Create `frontend/.dockerignore`**.
- [ ] **Add API URL abstraction** to frontend code (`apiUrl()` helper).
- [ ] **Build and test frontend image locally**:
  ```bash
  cd frontend && docker build -t fg-web --build-arg VITE_API_URL="" .
  docker run --rm -p 3000:8080 fg-web
  ```
- [ ] **Update `docker-compose.yml`** to include all 3 services (see `07_docker_compose_dev.md`).
- [ ] **Test full stack**: `docker compose up --build` — verify end to end.
- [ ] **Create `.env.example`** with placeholder values.

## Phase 2: GCP Project Setup

- [ ] **Create GCP project** `focusgroups-prod` (or confirm it exists).
- [ ] **Enable APIs**:
  ```bash
  gcloud services enable \
      sqladmin.googleapis.com \
      run.googleapis.com \
      artifactregistry.googleapis.com \
      secretmanager.googleapis.com
  ```
- [ ] **Create service account** `focusgroups-api` with minimal roles.
- [ ] **Create Artifact Registry** repository.
- [ ] **Create secrets** in Secret Manager (`pg-password`, `anthropic-api-key`, `fg-api-key`).

## Phase 3: Database Migration

- [ ] **Create Cloud SQL instance** (confirm cost with user first).
- [ ] **Enable pgvector** extension.
- [ ] **Apply schema** (`db/init.sql`).
- [ ] **Dump local data**: `pg_dump -Fc -f focusgroups.dump`
- [ ] **Restore to Cloud SQL** via proxy.
- [ ] **Verify data**: spot-check row counts, run a few queries.

## Phase 4: Deploy Services

- [ ] **Push backend image** to Artifact Registry.
- [ ] **Deploy `focusgroups-api`** to Cloud Run with Cloud SQL connector + secrets.
- [ ] **Verify API**: `curl https://focusgroups-api-xxx.run.app/health`
- [ ] **Get API URL** for frontend build.
- [ ] **Push frontend image** to Artifact Registry (with `VITE_API_URL` set).
- [ ] **Deploy `focusgroups-web`** to Cloud Run.
- [ ] **Update CORS_ORIGINS** on backend to include frontend URL.
- [ ] **End-to-end test**: create a session through the deployed frontend.

## Phase 5: CI/CD

- [ ] **Set up Workload Identity Federation** for GitHub Actions.
- [ ] **Create `.github/workflows/deploy.yml`**.
- [ ] **Add GitHub secrets** (`WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`).
- [ ] **Test pipeline**: push to main, verify auto-deploy.

## Phase 6: Production Hardening

- [ ] **Set `--min-instances=1`** on API if cold start latency is a problem.
- [ ] **Configure Cloud SQL backups** (automated daily + weekly GCS export).
- [ ] **Set up monitoring**: Cloud Run metrics, Cloud SQL metrics, error alerting.
- [ ] **Custom domain** (optional): map via Cloud Run domain mappings.
- [ ] **Remove public IP** from Cloud SQL instance (use private IP / built-in connector only).
- [ ] **Review IAM**: ensure no over-permissioned accounts.

## Rollback Plan

If anything goes wrong after migration:
1. Local stack is unchanged — `docker compose up db` + local uvicorn still works.
2. Cloud SQL data can be restored from backup.
3. Cloud Run revisions can be rolled back: `gcloud run services update-traffic focusgroups-api --to-revisions=PREVIOUS_REVISION=100`
