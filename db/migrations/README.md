# Database Migrations

## Convention

Migration files are numbered SQL scripts applied in order:

```
001_add_soft_delete_and_name.sql
002_normalize_tags_sectors_models.sql
003_sessions.sql
...
```

### Rules

1. **Prefix**: 3-digit zero-padded number (`001`, `002`, ...).
2. **Suffix**: descriptive snake_case name ending in `.sql`.
3. **Idempotent when possible**: use `IF NOT EXISTS`, `IF EXISTS`, `ADD COLUMN IF NOT EXISTS`.
4. **Wrap in a transaction**: use `BEGIN; ... COMMIT;` so failures roll back cleanly.
5. **Never modify an existing migration file** — create a new one instead.

## Applying Migrations

Use the migration runner script:

```bash
db/migrate.sh
```

This script:
- Creates a `schema_migrations` table if it doesn't exist (tracks applied migrations).
- Finds all `NNN_*.sql` files in `db/migrations/`.
- Applies any that haven't been recorded in `schema_migrations`, in numeric order.
- Records each successful migration with a timestamp.

### Required Environment Variables

| Variable      | Default     | Description             |
|---------------|-------------|-------------------------|
| `PG_HOST`     | `localhost` | Postgres host           |
| `PG_PORT`     | `5432`      | Postgres port           |
| `PG_USER`     | `fg_user`   | Postgres user           |
| `PG_PASSWORD` | (none)      | Postgres password       |
| `PG_DB`       | `focusgroups` | Postgres database name |

### Fresh Instances

For brand-new databases, run `db/init.sql` first — it contains the full schema.
Migrations are only needed for **existing** databases that need incremental upgrades.
