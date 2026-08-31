# Phase 4 — Moteur d'analyse décisionnelle

Ce document décrit l'objectif, le fonctionnement et la validation de la Phase 4
du projet (moteur d'analyse / règles métier / recommandations).

Objectif
--------

Le moteur d'analyse consolide des KPI (occupation, admissions, dépenses,
consommation, effectifs, budgets, etc.), applique des règles métier et
produit des recommandations destinées à la direction. Les analyses peuvent
être lancées à la demande via l'API et peuvent être persistées pour l'historique.

Règles métier disponibles
-------------------------

1. `saturation_v1` — détecte la saturation globale et par service (taux
   d'occupation élevé). Retourne un `service_issue` quand un service particulier
   est en cause.
2. `budget_overrun_v1` — compare dépenses vs budgets par service et signale
   les dépassements (warning/alert/critical selon la gravité).
3. `energy_anomaly_v1` — détecte des anomalies de consommation énergétique
   par rapport à un baseline historique.
4. `staff_shortage_v1` — identifie des risques d'insuffisance d'effectifs
   (par ex. admissions par infirmier supérieures aux seuils).

Seuils par défaut
-----------------

Les seuils par défaut sont définis dans le code mais peuvent être surchargés
via la configuration (voir ci-dessous). Valeurs par défaut (extrait) :

- Saturation globale: warning=0.90, alert=0.95, critical=0.98
- Saturation service: warning=0.95, alert=0.98, critical=1.00
- Budget: warning_pct=0.05, alert_pct=0.10, critical_pct=1.0
- Energy multipliers: warning=1.5, alert=2.0, critical=3.0
- Staff (nurse): warning=3.0, alert=5.0, critical=7.0

Configuration des seuils (`ANALYSIS_THRESHOLDS`)
---------------------------------------------

V1 simple et locale : les seuils peuvent être fournis en JSON soit via la
variable d'environnement `ANALYSIS_THRESHOLDS` (valeur = chemin vers un fichier
JSON OU chaîne JSON brute), soit via un fichier `backend/app/config/thresholds.json`.

La configuration est fusionnée (deep-merge) avec les valeurs par défaut : seules
les clés fournies écrasent les paramètres par défaut, les autres restent
inchangés.

Exemples :

1. JSON string dans l'env :

   export ANALYSIS_THRESHOLDS='{"saturation": {"global": {"warning": 0.85}}}'

2. Fichier `backend/app/config/thresholds.json` contenant le JSON.

L'implémentation V1 est volontairement simple (pas de table dans la DB) pour
rester légère et testable.

API — lancer et consulter une analyse
-------------------------------------

- Lancer une analyse (persistée) : POST `/analyses`
  - Payload exemple : `{"start": "2026-08-31", "end": "2026-08-31", "triggered_by":"e2e-scenario"}`
  - Réponse: 201 Created, body `{ "analysis_id": <id>, "status": "created" }`

- Récupérer une analyse : GET `/analyses/{id}`
  - Retourne le snapshot KPI, `rule_results`, `risk_level`, `anomalies` et `recommendations`.

- Consulter l'historique : GET `/analyses` (options `service` et `date` en query).

- Accepter / rejeter une recommandation : PATCH `/recommendations/{id}`
  - Payload: `{ "status": "accepted" }` ou `{"status":"rejected"}`

Scénarios de test disponibles
----------------------------

- `normal` — scénario de charge normale (ne doit pas déclencher les règles critiques).
- `saturation` — scénario conçu pour produire forte occupation et détecter la saturation.
- `budget_overrun` — scénario conçu pour produire dépassements budgétaires sur un horizon court.

Critères de validation de la Phase 4
-----------------------------------

1. Les règles s'exécutent et retournent un rapport structuré (`rule_results`).
2. Les recommandations peuvent être persistées et référencent `service_id`
   quand un service spécifique est identifié.
3. Les scénarios `normal`, `saturation`, `budget_overrun` doivent être
   reproductibles (seed fixe) et déclencher ou non les règles attendues.
4. Les seuils sont configurables via `ANALYSIS_THRESHOLDS` et les tests
   couvrent comportement par défaut et overrides.

Notes opérationnelles
---------------------

- Les warnings SQLAlchemy existent et ne sont pas modifiés dans cette phase.
- Les seuils métier n'ont pas été modifiés — seules des options de configuration
  ont été ajoutées pour les surcharger au besoin.