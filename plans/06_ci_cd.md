# 06 — CI/CD Pipeline

## Option A: GitHub Actions (Recommended)

Simpler, free for public repos, integrates with existing GitHub workflow.

### `.github/workflows/deploy.yml`

```yaml
name: Build & Deploy

on:
  push:
    branches: [main]

env:
  PROJECT_ID: focusgroups-prod
  REGION: us-central1
  API_IMAGE: us-central1-docker.pkg.dev/focusgroups-prod/focusgroups/api
  WEB_IMAGE: us-central1-docker.pkg.dev/focusgroups-prod/focusgroups/web

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_USER: fg_user
          POSTGRES_PASSWORD: localdev
          POSTGRES_DB: focusgroups
        ports:
          - 5432:5432
        options: >-
          --health-cmd="pg_isready -U fg_user -d focusgroups"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=5
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -e .
          pip install pytest

      - name: Init DB schema
        run: psql -h localhost -U fg_user -d focusgroups -f db/init.sql
        env:
          PGPASSWORD: localdev

      - name: Run tests
        run: python3 -m pytest tests/ -v
        env:
          PG_HOST: localhost
          PG_PASSWORD: localdev
          PG_DB: focusgroups
          PG_USER: fg_user

  deploy-api:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # for Workload Identity Federation
    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker us-central1-docker.pkg.dev

      - name: Build and push API image
        run: |
          docker build -t $API_IMAGE:${{ github.sha }} -t $API_IMAGE:latest .
          docker push $API_IMAGE --all-tags

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy focusgroups-api \
            --image=$API_IMAGE:${{ github.sha }} \
            --region=$REGION \
            --quiet

  deploy-web:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker us-central1-docker.pkg.dev

      - name: Get API URL
        id: api-url
        run: |
          URL=$(gcloud run services describe focusgroups-api --region=$REGION --format='value(status.url)')
          echo "url=$URL" >> $GITHUB_OUTPUT

      - name: Build and push Web image
        run: |
          cd frontend
          docker build -t $WEB_IMAGE:${{ github.sha }} -t $WEB_IMAGE:latest \
            --build-arg VITE_API_URL=${{ steps.api-url.outputs.url }} .
          docker push $WEB_IMAGE --all-tags

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy focusgroups-web \
            --image=$WEB_IMAGE:${{ github.sha }} \
            --region=$REGION \
            --quiet
```

### Workload Identity Federation Setup

Avoids storing GCP service account keys in GitHub:

```bash
# Create a Workload Identity Pool
gcloud iam workload-identity-pools create github-pool \
    --location=global

# Create a provider for GitHub
gcloud iam workload-identity-pools providers create-oidc github-provider \
    --location=global \
    --workload-identity-pool=github-pool \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository"

# Grant the GitHub repo permission to impersonate the SA
gcloud iam service-accounts add-iam-policy-binding \
    focusgroups-api@focusgroups-prod.iam.gserviceaccount.com \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_ORG/focus_groups"
```

## Option B: Cloud Build

Alternative if you want everything in GCP. Useful if you prefer trigger-based builds.

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', '$_API_IMAGE:$COMMIT_SHA', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', '$_API_IMAGE:$COMMIT_SHA']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    args: ['gcloud', 'run', 'deploy', 'focusgroups-api',
           '--image=$_API_IMAGE:$COMMIT_SHA',
           '--region=us-central1']
```

**Recommendation**: Use GitHub Actions. It's where the code already lives, and Workload Identity Federation is more secure than storing SA keys.

## GitHub Actions Secrets Required

| Secret | Value |
|--------|-------|
| `WIF_PROVIDER` | `projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `WIF_SERVICE_ACCOUNT` | `focusgroups-api@focusgroups-prod.iam.gserviceaccount.com` |

No GCP credentials stored as secrets — WIF handles auth via OIDC tokens.
