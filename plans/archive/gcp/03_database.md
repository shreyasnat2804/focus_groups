# 03 — Database (Cloud SQL)

## Current State

- Local Postgres 16 + pgvector via `docker-compose.yml` (`pgvector/pgvector:pg16` image)
- Schema in `db/init.sql`
- Connection via env vars: `PG_HOST`, `PG_PORT`, `PG_USER`, `PG_PASSWORD`, `PG_DB`

## Cloud SQL Setup

### Instance Creation

```bash
# Requires user confirmation — costs ~$50-80/mo
gcloud sql instances create focusgroups-db \
    --database-version=POSTGRES_16 \
    --tier=db-custom-2-8192 \
    --region=us-central1 \
    --storage-size=50GB \
    --storage-auto-increase \
    --database-flags=cloudsql.enable_pgvector=on \
    --backup-start-time=04:00 \
    --maintenance-window-day=SUN \
    --maintenance-window-hour=5

# Create database
gcloud sql databases create focusgroups --instance=focusgroups-db

# Create user
gcloud sql users create fg_user \
    --instance=focusgroups-db \
    --password="$(openssl rand -base64 24)"
```

### Enable pgvector

After instance is up, connect and run:
```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### Apply Schema

Run `db/init.sql` against the Cloud SQL instance via Cloud SQL Proxy:
```bash
cloud-sql-proxy focusgroups-prod:us-central1:focusgroups-db &
psql -h 127.0.0.1 -U fg_user -d focusgroups -f db/init.sql
```

## Connection Pattern: Cloud Run → Cloud SQL

Cloud Run has **built-in Cloud SQL connector** — no need for a separate proxy sidecar.

### How it works

1. Deploy with `--add-cloudsql-instances=PROJECT:REGION:INSTANCE`
2. Cloud Run mounts a Unix socket at `/cloudsql/PROJECT:REGION:INSTANCE`
3. Set `PG_HOST=/cloudsql/focusgroups-prod:us-central1:focusgroups-db`

### Code Change in `db.py`

The current `_pg_kwargs()` works as-is. When `PG_HOST` starts with `/`, psycopg2 uses it as a Unix socket directory. No code change needed — just set the env var correctly.

One consideration: when using Unix sockets, `PG_PORT` is ignored. The current code already falls back to defaults, so this is fine.

## Data Migration (Local → Cloud SQL)

### Option A: pg_dump / pg_restore (recommended for <10GB)

```bash
# Dump from local
pg_dump -h localhost -U fg_user -d focusgroups -Fc -f focusgroups.dump

# Restore to Cloud SQL (via proxy)
cloud-sql-proxy focusgroups-prod:us-central1:focusgroups-db &
pg_restore -h 127.0.0.1 -U fg_user -d focusgroups --no-owner focusgroups.dump
```

### Option B: Cloud SQL Import (for larger datasets)

```bash
# Upload dump to GCS
gsutil cp focusgroups.dump gs://focusgroups-data/migration/

# Import via Cloud SQL API
gcloud sql import sql focusgroups-db gs://focusgroups-data/migration/focusgroups.dump \
    --database=focusgroups
```

## Schema Migrations Strategy

Currently using a single `init.sql` file. For production:

1. **Keep `init.sql` as the baseline** — used for fresh instances and local dev.
2. **Add a `db/migrations/` directory** for incremental changes:
   ```
   db/
     init.sql              # full schema (local dev / new instances)
     migrations/
       001_add_session_name.sql
       002_add_soft_delete.sql
       ...
   ```
3. **Use a lightweight migration runner** — either:
   - Manual: numbered SQL files applied in order via a shell script
   - Library: `yoyo-migrations` or `alembic` (alembic is heavier but more standard)

   **Recommendation**: Start with numbered SQL files + a simple apply script. Move to alembic only if schema changes become frequent.

## Backups

Cloud SQL provides automatic daily backups (configured with `--backup-start-time`). Additionally:

- Enable point-in-time recovery (PITR) for the first few months
- Export to GCS weekly as an extra safety net:
  ```bash
  gcloud sql export sql focusgroups-db gs://focusgroups-data/backups/$(date +%Y%m%d).sql \
      --database=focusgroups
  ```

## Networking / Security

- Cloud SQL instance should have **no public IP** — use private IP + VPC connector, or rely on Cloud SQL Auth Proxy (built into Cloud Run).
- IAM: the Cloud Run service account needs `roles/cloudsql.client`.
- Do NOT whitelist `0.0.0.0/0` on the Cloud SQL instance.
