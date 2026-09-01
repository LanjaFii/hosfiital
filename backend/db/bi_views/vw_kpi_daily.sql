-- vw_kpi_daily: hôpital / jour. Direct mapping à la table kpi_daily.
-- Ne génère aucune granularité service, respecte le contenu existant de kpi_daily.
CREATE OR REPLACE VIEW vw_kpi_daily AS
SELECT
  day::date AS day,
  admissions_total,
  discharges_total,
  occupied_beds_total,
  capacity_total,
  occupancy_rate,
  expenses_total,
  energy_total
FROM kpi_daily;
