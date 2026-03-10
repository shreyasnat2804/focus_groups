# 04 — Secrets & Configuration

## Current State

All secrets in a flat `.env` file:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` (for docker-compose)
- `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DB` (for app)
- `ANTHROPIC_API_KEY`

No `FG_API_KEY` set locally (auth disabled in dev).

## Secret Manager Setup

### Create Secrets

```bash
# Create secrets (values set separately)
gcloud secrets create pg-password --replication-policy=automatic
gcloud secrets create anthropic-api-key --replication-policy=automatic
gcloud secrets create fg-api-key --replication-policy=automatic

# Set values
echo -n "ACTUAL_PASSWORD" | gcloud secrets versions add pg-password --data-file=-
echo -n "sk-ant-..." | gcloud secrets versions add anthropic-api-key --data-file=-
echo -n "$(openssl rand -base64 32)" | gcloud secrets versions add fg-api-key --data-file=-
```

### Grant Access to Cloud Run Service Account

```bash
SA="focusgroups-api@focusgroups-prod.iam.gserviceaccount.com"

for secret in pg-password anthropic-api-key fg-api-key; do
  gcloud secrets add-iam-policy-binding $secret \
      --member="serviceAccount:$SA" \
      --role="roles/secretAccessor"
done
```

### Mount as Env Vars on Cloud Run

```bash
gcloud run deploy focusgroups-api \
    --set-secrets="PG_PASSWORD=pg-password:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,FG_API_KEY=fg-api-key:latest"
```

Cloud Run injects these as regular environment variables at container start. The app code reads them with `os.getenv()` — no code changes needed.

## Environment Variable Matrix

| Variable | Local (`.env`) | Cloud Run | Source |
|----------|---------------|-----------|--------|
| `PG_HOST` | `localhost` | `/cloudsql/project:region:instance` | Plain env var |
| `PG_PORT` | `5432` | (not set — Unix socket) | Plain env var |
| `PG_DB` | `focusgroups` | `focusgroups` | Plain env var |
| `PG_USER` | `fg_user` | `fg_user` | Plain env var |
| `PG_PASSWORD` | `localdev` | (from Secret Manager) | Secret |
| `ANTHROPIC_API_KEY` | `sk-ant-...` | (from Secret Manager) | Secret |
| `FG_API_KEY` | (not set) | (from Secret Manager) | Secret |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | `https://focusgroups-web-xxx.run.app` | Plain env var |
| `LOG_FORMAT` | `json` | `json` | Plain env var |
| `LOG_LEVEL` | `INFO` | `INFO` | Plain env var |

## IAM Service Accounts

### Create a Dedicated Service Account

Don't use the default Compute Engine SA. Create a minimal one:

```bash
gcloud iam service-accounts create focusgroups-api \
    --display-name="Focus Groups API"

SA="focusgroups-api@focusgroups-prod.iam.gserviceaccount.com"

# Cloud SQL client access
gcloud projects add-iam-policy-binding focusgroups-prod \
    --member="serviceAccount:$SA" \
    --role="roles/cloudsql.client"

# Secret accessor
gcloud projects add-iam-policy-binding focusgroups-prod \
    --member="serviceAccount:$SA" \
    --role="roles/secretmanager.secretAccessor"

# Cloud Storage read (for model weights if needed later)
gcloud projects add-iam-policy-binding focusgroups-prod \
    --member="serviceAccount:$SA" \
    --role="roles/storage.objectViewer"
```

### Use It on Cloud Run

```bash
gcloud run deploy focusgroups-api \
    --service-account=$SA
```

## .env File Policy

- `.env` is in `.gitignore` (verify this).
- Never commit `.env` to git.
- Provide a `.env.example` with placeholder values for onboarding:

```env
# .env.example — copy to .env and fill in values
PG_HOST=localhost
PG_PORT=5432
PG_DB=focusgroups
PG_USER=fg_user
PG_PASSWORD=localdev
ANTHROPIC_API_KEY=your-key-here
# FG_API_KEY=  # leave unset to disable auth in dev
# CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```
