# 05 — Cloud Run Deployment

## Services

| Service | Image | Memory | CPU | Min Instances | Max Instances |
|---------|-------|--------|-----|---------------|---------------|
| `focusgroups-api` | `us-central1-docker.pkg.dev/focusgroups-prod/focusgroups/api` | 2Gi | 2 | 0 | 5 |
| `focusgroups-web` | `us-central1-docker.pkg.dev/focusgroups-prod/focusgroups/web` | 256Mi | 1 | 0 | 3 |

## Artifact Registry

```bash
# Create Docker repository
gcloud artifacts repositories create focusgroups \
    --repository-format=docker \
    --location=us-central1

# Configure docker auth
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## Backend Deployment

```bash
IMAGE="us-central1-docker.pkg.dev/focusgroups-prod/focusgroups/api"

# Build and push
docker build -t $IMAGE:latest -t $IMAGE:$(git rev-parse --short HEAD) .
docker push $IMAGE --all-tags

# Deploy
gcloud run deploy focusgroups-api \
    --image=$IMAGE:latest \
    --region=us-central1 \
    --platform=managed \
    --service-account=focusgroups-api@focusgroups-prod.iam.gserviceaccount.com \
    --allow-unauthenticated \
    --memory=2Gi \
    --cpu=2 \
    --timeout=300 \
    --concurrency=20 \
    --min-instances=0 \
    --max-instances=5 \
    --add-cloudsql-instances=focusgroups-prod:us-central1:focusgroups-db \
    --set-env-vars="PG_HOST=/cloudsql/focusgroups-prod:us-central1:focusgroups-db,PG_DB=focusgroups,PG_USER=fg_user,CORS_ORIGINS=https://focusgroups.example.com,LOG_FORMAT=json" \
    --set-secrets="PG_PASSWORD=pg-password:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,FG_API_KEY=fg-api-key:latest" \
    --port=8080 \
    --startup-probe-path=/health \
    --liveness-probe-path=/health
```

### Key Settings Explained

- **`--timeout=300`**: Claude API calls can take 30-60s per persona. A session with 10+ personas needs headroom.
- **`--concurrency=20`**: Each container can handle 20 concurrent requests (gunicorn has 2 workers, each handles 10 via async).
- **`--min-instances=0`**: Scale to zero when idle to save cost. Set to 1 if cold start latency matters.
- **`--max-instances=5`**: Safety cap to prevent runaway costs.

## Frontend Deployment

```bash
IMAGE="us-central1-docker.pkg.dev/focusgroups-prod/focusgroups/web"
API_URL="https://focusgroups-api-HASH-uc.a.run.app"

cd frontend
docker build -t $IMAGE:latest --build-arg VITE_API_URL=$API_URL .
docker push $IMAGE:latest

gcloud run deploy focusgroups-web \
    --image=$IMAGE:latest \
    --region=us-central1 \
    --platform=managed \
    --allow-unauthenticated \
    --memory=256Mi \
    --cpu=1 \
    --min-instances=0 \
    --max-instances=3 \
    --port=8080 \
    --startup-probe-path=/health
```

## Custom Domain (Optional)

```bash
# Map domain
gcloud run domain-mappings create \
    --service=focusgroups-web \
    --domain=focusgroups.example.com \
    --region=us-central1

# Map API subdomain
gcloud run domain-mappings create \
    --service=focusgroups-api \
    --domain=api.focusgroups.example.com \
    --region=us-central1
```

Then update DNS with the CNAME records GCP provides.

## Networking Considerations

### Frontend → Backend Communication

Two options:

**Option A: Direct cross-origin calls (recommended initially)**
- Frontend calls `https://focusgroups-api-xxx.run.app/api/...` directly.
- CORS is already configured — just update `CORS_ORIGINS` to include the frontend URL.
- Simple, no extra infrastructure.

**Option B: API Gateway / Load Balancer (later)**
- Put both services behind a single Cloud Load Balancer.
- Route `/api/*` to backend, `/*` to frontend.
- Single domain, no CORS needed.
- More complex, but cleaner for end users.

**Recommendation**: Start with Option A. Move to a load balancer if/when you add a custom domain.

### Cloud Run → Cloud SQL

Built-in Cloud SQL connector via `--add-cloudsql-instances`. No VPC connector needed for this alone.

## Cost Estimates

| Component | Monthly Est. |
|-----------|-------------|
| Cloud Run API (low traffic, scale-to-zero) | $5-15 |
| Cloud Run Web (low traffic, scale-to-zero) | $2-5 |
| Artifact Registry (a few images) | $1-2 |
| Total (Cloud Run + Registry) | $8-22 |

Combined with Cloud SQL ($50-80), total infra: **~$60-100/mo**.
