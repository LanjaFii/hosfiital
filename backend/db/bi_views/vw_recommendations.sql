-- vw_recommendations: expose recommendations joined with their analysis JSONB (kpi_snapshot, anomalies)
-- severity and evidence are extracted from analyses.anomalies / analyses.kpi_snapshot when possible.
-- We do not invent fields such as resolved_at or suggested_actions.

CREATE OR REPLACE VIEW vw_recommendations AS
SELECT
  r.id AS recommendation_id,
  r.analysis_id,
  r.service_id,
  svc.name AS service_name,
  r.type AS rule_id,
  r.text,
  r.status,
  r.created_at,
  a.risk_level,
  a.triggered_by,
  a.triggered_at,
  a.kpi_snapshot,
  a.anomalies,
  -- extract severity from anomalies JSONB array when a matching rule element exists
  (matched.elem->> 'severity')::text AS severity,
  -- keep raw evidence snippet (values) if present for the matched anomaly
  (matched.elem-> 'values') AS evidence
FROM recommendations r
LEFT JOIN analyses a ON a.id = r.analysis_id
LEFT JOIN services svc ON svc.id = r.service_id
LEFT JOIN LATERAL (
  -- find first anomaly element whose rule_id matches recommendation.type
  SELECT elem
  FROM jsonb_array_elements(a.anomalies) AS elem
  WHERE (elem->> 'rule_id') = r.type
  LIMIT 1
) AS matched ON true;
