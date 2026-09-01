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
Applied change in this repository
- The `compose.yaml` was updated to add a dedicated metadata Postgres service `metabase_db` and to set `MB_DB_*` env variables for the `metabase` service.

What changed (non-destructive)
- Added service `metabase_db` (Postgres) with DB `metabase` and user `metabase` (password `metabase_pass`).
- Configured `metabase` service to use `MB_DB_*` env pointing to `metabase_db` so Metabase will persist metadata there instead of the embedded H2 file.
- Added Docker volume `metabase_data` to persist the metadata DB files.

Credentials and secrets
- The compose file contains plaintext credentials for convenience in a development environment. In production, replace these with secrets or environment overrides.

How to start and validate (non-destructive)
1) Validate compose file syntax:

```bash
docker compose config
```

2) Start the metadata DB and Metabase (detached):

```bash
docker compose up -d metabase_db metabase
```

3) Check container status and logs:

```bash
docker compose ps
docker compose logs --tail=200 metabase
```

4) Verify Metabase connected to its metadata DB: look for log lines indicating successful DB migration/initialization and startup (Metabase will report it is listening on port 3000).

Notes
- This approach keeps the application DB (`hosfiital`) untouched.
- If you prefer the metadata DB to live in the existing Postgres instance, revert the `metabase` env to point to `postgres` and create the `metabase` DB/user on that server (instructions remain in the doc).

Security & production notes
- Use strong passwords and secrets management (do not store plaintext secrets in compose file in production).
- Prefer dedicated metabase DB and user with limited privileges.

End of document.

Imported Dashboard
------------------
During setup we created and imported the Dashboard "A - Vue générale de l'hôpital" directly into Metabase metadata. Details:

- Metabase `database_id`: 2 (hosfiital datasource)
- Dashboard id: 2
- Cards created (IDs):
  - 40: Admissions - série temporelle
  - 41: Sorties - série temporelle
  - 42: Occupation vs Capacité - série temporelle
  - 43: Dépenses et consommation énergétique
  - 44: Résumé par service (dernier jour)
  - 45: Aperçu des risques / recommandations

These cards are native SQL questions that query the `vw_*` views. They were validated by executing the same SQL directly against the `hosfiital` DB (results ok — may be zeros depending on seeded data).

To remove the dashboard from Metabase, delete the `report_dashboard` row with id=2 in the metabase metadata DB or use the Metabase UI to delete it. Do not remove application data.

Imported Dashboard C
--------------------
Le dashboard "C - Capacité & Occupation" a été importé dans Metabase metadata.

- Dashboard id: 3
- Cards ids:
  - 46: Tendance - Capacité totale
  - 47: Tendance - Taux d'occupation (global)
  - 48: Occupation horaire par service (dernier 7 jours)
  - 49: Capacité par service (dernier jour)
  - 50: Services avec taux d'occupation élevé

Ces cartes utilisent exclusivement les vues `vw_kpi_daily`, `vw_occupancy_timeseries` et `vw_service_summary` et ont été validées en exécutant leurs SQL directement sur la base `hosfiital`.

Imported Dashboard G
--------------------
Le dashboard "G - Risques & Recommandations" a été importé dans Metabase metadata.

- Dashboard id: 4
- Cards ids:
  - 51: Risques par gravité
  - 52: Recommandations par service
  - 53: Détails recommandations (dernier 30 jours)
  - 54: KPI snapshot sample

Ces cartes exploitent `vw_recommendations` et affichent `severity`, `evidence`, `kpi_snapshot` et le texte des recommandations. Les requêtes ont été testées directement sur la base `hosfiital`.
