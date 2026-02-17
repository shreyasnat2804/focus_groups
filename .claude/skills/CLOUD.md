# CLOUD.md — GCP Infrastructure

## Project Structure

```
GCP Project: focusgroups-prod
Region: us-central1 (cheapest for Cloud SQL + Cloud Run)
```

## Services

### Cloud SQL (Postgres 16 + pgvector)

```bash
# Create instance (ask permission — this costs money)
gcloud sql instances create focusgroups-db \
    --database-version=POSTGRES_16 \
    --tier=db-custom-2-8192 \
    --region=us-central1 \
    --storage-size=50GB \
    --database-flags=cloudsql.enable_pgvector=on

# Create database
gcloud sql databases create focusgroups --instance=focusgroups-db

# Connect via proxy
cloud-sql-proxy focusgroups-prod:us-central1:focusgroups-db &
psql -h 127.0.0.1 -U fg_user -d focusgroups
```

### Cloud Storage

```
gs://focusgroups-data/         — Raw exports, PANDORA dataset, CSV dumps
gs://focusgroups-models/       — LoRA checkpoints, classifier weights
gs://focusgroups-frontend/     — React build artifacts (if using static hosting)
```

```bash
gsutil mb -l us-central1 gs://focusgroups-data
gsutil mb -l us-central1 gs://focusgroups-models
```

### Cloud Run — Backend (FastAPI)

```bash
# Build and deploy
gcloud run deploy focusgroups-api \
    --source=./backend \
    --region=us-central1 \
    --allow-unauthenticated \
    --set-env-vars="PG_HOST=/cloudsql/focusgroups-prod:us-central1:focusgroups-db" \
    --add-cloudsql-instances=focusgroups-prod:us-central1:focusgroups-db \
    --memory=2Gi \
    --cpu=2
```

### Cloud Run — Frontend (React)

```bash
gcloud run deploy focusgroups-web \
    --source=./frontend \
    --region=us-central1 \
    --allow-unauthenticated \
    --memory=512Mi \
    --cpu=1
```

## IAM & Service Accounts

```
focusgroups-api@focusgroups-prod.iam.gserviceaccount.com
  → roles/cloudsql.client
  → roles/storage.objectViewer
```

## Cost Estimates

| Service | Monthly Est. |
|---------|-------------|
| Cloud SQL (db-custom-2-8192) | ~$50-80 |
| Cloud Run (API, low traffic) | ~$5-15 |
| Cloud Storage (100GB) | ~$2 |
| **Total** | **~$60-100/mo** |

## Pitfalls

- **Cloud SQL Auth Proxy**: Required for Cloud Run → Cloud SQL connections. Use Unix socket path, not TCP.
- **pgvector on Cloud SQL**: Enable via database flag `cloudsql.enable_pgvector=on`, then `CREATE EXTENSION vector;` inside the database.
- **Cold starts on Cloud Run**: Set `--min-instances=1` if latency matters. Costs more.
- **Don't create resources without asking**: All `gcloud create` commands require user confirmation.
