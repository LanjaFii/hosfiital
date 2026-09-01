PHASE 5 — Metabase configuration and persistence

Goal
- Run Metabase connected to the project PostgreSQL and persist Metabase metadata in a Postgres DB (preferred) or via Docker volume.

Current compose.yaml
- There is an existing `postgres` service exposing database `hosfiital` (user `hosfiital`).
- Metabase service exists but currently uses default internal H2 (no MB_DB_* env vars) and no persistence volume for Metabase metadata.

Recommended options
1) Use existing Postgres server for Metabase metadata (recommended for dev/prod):
   - Create a dedicated database and user on the same Postgres instance: `metabase` DB, user `metabase`.
   - Configure Metabase with environment variables `MB_DB_*` (see below).
   - Pros: easier backups, no need for extra container; Cons: share same DB instance (acceptable with proper credentials/limits).

2) Use a dedicated Postgres service for Metabase metadata (compose):
   - Add a new service `metabase_db` in `compose.yaml` and configure Metabase to use it via `MB_DB_*`.
   - Pros: isolated DB, easier to size independently; Cons: extra container and volume.

3) Use Docker volume for H2 (not recommended for production):
   - Map a volume (e.g., `metabase_data:/metabase-data`) but H2 is less robust than Postgres for production use.

What I will prepare
- A documentation file with exact commands to:
  - create `metabase` database and user on the existing Postgres,
  - set environment variables for Metabase,
  - sample compose snippet (non-destructive) to show how to set MB_DB_* env vars,
  - instructions to start Metabase and check connectivity,
  - backup/restore steps for Metabase metadata.

Action items (manual steps to perform)
1) Create Metabase database and user on existing Postgres (run as DB admin):

```sql
-- connect as postgres superuser or hosfiital user with sufficient rights
CREATE DATABASE metabase;
CREATE USER metabase WITH PASSWORD 'metabase_pass';
GRANT ALL PRIVILEGES ON DATABASE metabase TO metabase;
```

2) Example `compose` env for Metabase (add to `metabase` service env section):

```yaml
    environment:
      MB_DB_TYPE: "postgres"
      MB_DB_DBNAME: "metabase"
      MB_DB_PORT: 5432
      MB_DB_HOST: "postgres"
      MB_DB_USER: "metabase"
      MB_DB_PASS: "metabase_pass"
```

3) Persisting Metabase metadata using dedicated Postgres service (optional compose snippet):

```yaml
  metabase_db:
    image: postgres:17
    environment:
      POSTGRES_DB: metabase
      POSTGRES_USER: metabase
      POSTGRES_PASSWORD: metabase_pass
    volumes:
      - metabase_data:/var/lib/postgresql/data

  metabase:
    image: metabase/metabase:latest
    environment:
      MB_DB_TYPE: postgres
      MB_DB_DBNAME: metabase
      MB_DB_HOST: metabase_db
      MB_DB_PORT: 5432
      MB_DB_USER: metabase
      MB_DB_PASS: metabase_pass
    depends_on:
      - metabase_db
```

4) Start sequence (if using existing Postgres DB):

```bash
# Ensure Postgres is running
docker compose up -d postgres
# create metabase DB/user (see SQL above) using psql or PG admin tools
# Start Metabase (will use H2 by default if MB_DB_* not set)
docker compose up -d metabase
# If MB_DB_* envs are set, Metabase will initialize its metadata schema in the metabase DB
```

5) Verify Metabase metadata DB connectivity (example using psql):

```bash
PGPASSWORD=hosfiital_dev_password psql -h 127.0.0.1 -p 5433 -U hosfiital -d hosfiital -c "SELECT 1"
# as metabase user
PGPASSWORD=metabase_pass psql -h 127.0.0.1 -p 5433 -U metabase -d metabase -c "SELECT 1"
```

6) Initial Metabase setup
- Access http://localhost:3000 and follow the web wizard.
- When asked for application DB, choose Postgres and enter MB_DB_* credentials (if you configured them via compose env, Metabase will auto-use them at start).
- Add the project Postgres (`hosfiital`) as a datasource in Metabase using a read-only DB user (recommended to create `hosfiital_ro` for production-readonly access).

7) Backup & restore Metabase metadata
- If using Postgres for Metabase metadata: use `pg_dump`/`pg_restore` on the `metabase` DB.
- If using volume (H2) : ensure you backup the volume contents (not recommended for production).

Notes & checks performed
- Current `compose.yaml` includes `postgres` and `metabase` services. Metabase currently has no MB_DB_* env and no persistent volume.
- Recommended immediate action: create `metabase` DB + `metabase` user on existing Postgres, update `compose.yaml` or runtime environment to include MB_DB_* envs and restart Metabase.

Security & production notes
- Use strong passwords and secrets management (do not store plaintext secrets in compose file in production).
- Prefer dedicated metabase DB and user with limited privileges.

End of document.
