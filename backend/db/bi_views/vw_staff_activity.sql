-- vw_staff_activity: staff levels (as_of) with derived patients_per_fte if possible
-- Uses latest staff_levels rows as recorded (no synthetic absences data)

CREATE OR REPLACE VIEW vw_staff_activity AS
SELECT
  sl.id AS staff_level_id,
  sl.as_of,
  (sl.as_of::date) AS date,
  sl.service_id,
  svc.name AS service_name,
  sl.role,
  sl.headcount,
  sl.fte,
  -- compute patients per FTE for the date of the staff record using admissions on that date
  CASE WHEN sl.fte IS NULL OR sl.fte = 0 THEN NULL
       ELSE (COALESCE(adm.admissions_on_date,0)::numeric / NULLIF(sl.fte,0))
  END AS patients_per_fte
FROM staff_levels sl
LEFT JOIN services svc ON svc.id = sl.service_id
LEFT JOIN LATERAL (
  SELECT COUNT(*) AS admissions_on_date
  FROM admissions a
  WHERE a.service_id = sl.service_id
    AND a.admitted_at::date = sl.as_of::date
) adm ON true;
