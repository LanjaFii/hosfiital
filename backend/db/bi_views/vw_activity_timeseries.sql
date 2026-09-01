-- vw_activity_timeseries: activity records per period (typically daily) with optional avg_los computed from admissions
-- avg_los is computed only from admissions that have a non-null discharged_at on the same date.

CREATE OR REPLACE VIEW vw_activity_timeseries AS
SELECT
  ar.id AS activity_id,
  ar.period_start,
  ar.period_end,
  (ar.period_start::date) AS date,
  ar.service_id,
  svc.name AS service_name,
  ar.admissions_count,
  ar.discharges_count,
  ar.visits_count,
  -- average length of stay (days) for discharges occurring on the same period_start date
  avg_los_sub.avg_los
FROM activity_records ar
LEFT JOIN services svc ON svc.id = ar.service_id
LEFT JOIN LATERAL (
  SELECT AVG(EXTRACT(epoch FROM (a.discharged_at - a.admitted_at)) / 86400.0) AS avg_los
  FROM admissions a
  WHERE a.service_id = ar.service_id
    AND a.discharged_at IS NOT NULL
    AND a.discharged_at::date = ar.period_start::date
) avg_los_sub ON true;
