PHASE5 — Create read-only DB role for Metabase (`hosfiital_ro`)

Goal
- Provide exact SQL/commands to create a PostgreSQL role `hosfiital_ro` allowing only SELECT on the BI views (`vw_*`), with no write or schema modification rights.

Assumptions
- Your application DB is `hosfiital`, accessible on the Postgres container `hosfiital-postgres` (port 5433 on host).
- The BI views `vw_kpi_daily`, `vw_service_summary`, `vw_budget_variance`, `vw_recommendations`, `vw_occupancy_timeseries`, `vw_activity_timeseries`, `vw_staff_activity` are deployed in the `public` schema. If not yet deployed, apply `backend/db/bi_views/*.sql` first.

Create the role (run as DB superuser or owner, here executed via the postgres container using the `hosfiital` admin user):

```bash
# create the role with a password
docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -c "CREATE ROLE hosfiital_ro WITH LOGIN PASSWORD 'hosfiital_ro_pass';"

# allow connection to the database and usage of public schema
docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -c "GRANT CONNECT ON DATABASE hosfiital TO hosfiital_ro;"
docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -c "GRANT USAGE ON SCHEMA public TO hosfiital_ro;"

# Grant SELECT only on the BI views (explicit list to avoid overbroad rights)
docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -c "GRANT SELECT ON vw_kpi_daily, vw_service_summary, vw_budget_variance, vw_recommendations, vw_occupancy_timeseries, vw_activity_timeseries, vw_staff_activity TO hosfiital_ro;"
```

Optional: To make SELECT available on future tables/views in `public`, run as owner of the schema:

```sql
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO hosfiital_ro;
```

Testing the role
- Test read access (should succeed even if result set is empty):

```bash
docker exec -i hosfiital-postgres psql -U hosfiital_ro -d hosfiital -c "SELECT 1 FROM vw_kpi_daily LIMIT 1;"
```

- Test that write attempts are refused (example: creating a table in `public` should be denied):

```bash
docker exec -i hosfiital-postgres psql -U hosfiital_ro -d hosfiital -c "CREATE TABLE attempt_write_by_ro(id int);"
# Expected result: ERROR: permission denied for schema public
```

Notes and security
- Replace `hosfiital_ro_pass` with a secure password or use Docker secrets / environment injection.
- Granting `SELECT ON ALL TABLES IN SCHEMA public` is broader than necessary; prefer explicit GRANT on the BI views.
- This role has no write privileges by design. If Metabase requires additional access (e.g., to read other helper tables), add them explicitly.

Rollback (if needed)

```bash
# revoke grants then drop role
docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -c "REVOKE SELECT ON vw_kpi_daily, vw_service_summary, vw_budget_variance, vw_recommendations, vw_occupancy_timeseries, vw_activity_timeseries, vw_staff_activity FROM hosfiital_ro;"
docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -c "DROP ROLE IF EXISTS hosfiital_ro;"
```

End of document.
