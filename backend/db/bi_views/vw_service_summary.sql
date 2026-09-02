-- vw_service_summary: jour x service summary
-- Agrège séparément chaque source (occupancy, activity, expenses, energy, staff, capacity)
-- pour éviter multiplication de lignes. Pour capacity/staff on choisit la valeur la plus
-- récente <= date (utilisation de LATERAL DISTINCT ON pour "as_of" logic).

CREATE OR REPLACE VIEW vw_service_summary AS
WITH dates AS (
  -- union des dates présentes dans les sources pour couvrir les jours pertinents
  SELECT day::date AS d FROM kpi_daily
  UNION
  SELECT DISTINCT period_start::date FROM activity_records
  UNION
  SELECT DISTINCT snapshot_at::date FROM occupancy_snapshots
  UNION
  SELECT DISTINCT period_start::date FROM expenses
  UNION
  SELECT DISTINCT measured_at::date FROM energy_consumption
),
svcs AS (
  SELECT id AS service_id, name AS service_name FROM services
)
SELECT
  d.d::date AS date,
  s.service_id,
  s.service_name,
  -- latest capacity as of the date (NULL if none)
  -- prefer explicit capacity record; fallback to counting physical beds when missing
  COALESCE(cap.beds_total, (
    SELECT COUNT(*) FROM beds b WHERE b.service_id = s.service_id
  ))::integer AS beds_total,
  coalesce(occ.occupied_beds, 0)::integer AS occupied_beds,
  CASE WHEN COALESCE(cap.beds_total, (
        SELECT COUNT(*) FROM beds b WHERE b.service_id = s.service_id
      )) = 0 THEN NULL
       ELSE (coalesce(occ.occupied_beds,0)::numeric / NULLIF(COALESCE(cap.beds_total, (
            SELECT COUNT(*) FROM beds b WHERE b.service_id = s.service_id
          )),0)) * 100
  END AS occupancy_rate,
  coalesce(act.admissions,0)::integer AS admissions,
  coalesce(act.discharges,0)::integer AS discharges,
  coalesce(exp.expenses,0)::numeric AS expenses,
  b.budget_amount::numeric AS budget_amount,
  coalesce(en.energy_kwh,0)::numeric AS energy_kwh,
  coalesce(staff.staff_headcount,0)::integer AS staff_headcount
FROM dates d
CROSS JOIN svcs s
-- capacity: latest record on or before date for this service
LEFT JOIN LATERAL (
  SELECT sc.beds_total
  FROM service_capacity sc
  WHERE sc.service_id = s.service_id AND sc.as_of::date <= d.d
  ORDER BY sc.service_id, sc.as_of DESC
  LIMIT 1
) cap ON true
-- occupancy aggregated for the date
-- occupancy aggregated for the date (LATERAL to reference the date and service)
LEFT JOIN LATERAL (
  SELECT SUM(os.occupied_beds) AS occupied_beds
  FROM occupancy_snapshots os
  WHERE os.snapshot_at::date = d.d AND os.service_id = s.service_id
) occ ON true
-- activity aggregated for the date (LATERAL to reference the date and service)
LEFT JOIN LATERAL (
  SELECT SUM(ar.admissions_count) AS admissions, SUM(ar.discharges_count) AS discharges
  FROM activity_records ar
  WHERE ar.period_start::date = d.d AND ar.service_id = s.service_id
) act ON true
-- expenses aggregated for the date (LATERAL to reference the date and service)
LEFT JOIN LATERAL (
  SELECT SUM(e.amount) AS expenses
  FROM expenses e
  WHERE e.period_start::date = d.d AND e.service_id = s.service_id
) exp ON true
-- budgets: take budget for year of date if present
LEFT JOIN LATERAL (
  SELECT b.budget_amount
  FROM budgets b
  WHERE b.service_id = s.service_id AND b.year = EXTRACT(year FROM d.d)::int
  LIMIT 1
) b ON true
-- energy aggregated for the date (LATERAL)
LEFT JOIN LATERAL (
  SELECT SUM(ec.consumption_kwh) AS energy_kwh
  FROM energy_consumption ec
  WHERE ec.measured_at::date = d.d AND ec.service_id = s.service_id
) en ON true
-- staff: take latest headcount per role as of date and sum
LEFT JOIN LATERAL (
  SELECT SUM(t.headcount) AS staff_headcount
  FROM (
    SELECT DISTINCT ON (sl.service_id, sl.role) sl.service_id, sl.role, sl.headcount
    FROM staff_levels sl
    WHERE sl.service_id = s.service_id AND sl.as_of::date <= d.d
    ORDER BY sl.service_id, sl.role, sl.as_of DESC
  ) t
) staff ON true
;
