-- vw_occupancy_timeseries: raw occupancy snapshots with capacity and computed occupancy rate
-- Note: generator produces daily snapshots; hour may be present if timestamps are non-midnight.

CREATE OR REPLACE VIEW vw_occupancy_timeseries AS
SELECT
  os.id AS snapshot_id,
  os.snapshot_at,
  (os.snapshot_at::date) AS date,
  EXTRACT(hour FROM os.snapshot_at)::int AS hour,
  os.service_id,
  svc.name AS service_name,
  os.occupied_beds,
  os.available_beds,
  cap.beds_total::integer AS beds_total,
  CASE WHEN cap.beds_total IS NULL OR cap.beds_total = 0 THEN NULL
       ELSE (os.occupied_beds::numeric / NULLIF(cap.beds_total,0)) * 100
  END AS occupancy_rate
FROM occupancy_snapshots os
LEFT JOIN services svc ON svc.id = os.service_id
LEFT JOIN LATERAL (
  SELECT sc.beds_total
  FROM service_capacity sc
  WHERE sc.service_id = os.service_id AND sc.as_of::date <= os.snapshot_at::date
  ORDER BY sc.service_id, sc.as_of DESC
  LIMIT 1
) cap ON true;
