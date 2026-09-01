-- vw_budget_variance: variance budget vs dépenses
-- Logique retenue : présente la variance par service par année (budget.year).
-- Les dépenses sont agrégées sur l'année correspondante (year-to-date = total pour l'année).
-- Note: budgets sont annuels ; pour comparaisons sur d'autres périodes, filtrer côté requêtes.

CREATE OR REPLACE VIEW vw_budget_variance AS
SELECT
  b.service_id,
  s.name AS service_name,
  b.year,
  b.budget_amount::numeric AS budget_amount,
  COALESCE(exp.expenses_amount, 0)::numeric AS expenses_amount,
  (b.budget_amount::numeric - COALESCE(exp.expenses_amount,0)::numeric) AS variance_abs,
  CASE WHEN b.budget_amount IS NULL OR b.budget_amount = 0 THEN NULL
       ELSE ((b.budget_amount::numeric - COALESCE(exp.expenses_amount,0)::numeric) / NULLIF(b.budget_amount::numeric,0)) * 100
  END AS variance_pct
FROM budgets b
LEFT JOIN services s ON s.id = b.service_id
LEFT JOIN (
  -- sum of expenses for the budget year
  SELECT e.service_id, EXTRACT(year FROM e.period_start)::int AS yr, SUM(e.amount) AS expenses_amount
  FROM expenses e
  WHERE e.period_start IS NOT NULL
  GROUP BY e.service_id, EXTRACT(year FROM e.period_start)::int
) exp ON exp.service_id = b.service_id AND exp.yr = b.year
;
