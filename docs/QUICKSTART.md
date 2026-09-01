# QUICKSTART — Hosfiital (fiche de démarrage)

Ce guide court décrit comment démarrer l'infrastructure, initialiser la base, générer des données, lancer le pipeline ETL/KPI et exécuter une analyse à la demande. Il est conçu pour un usage local en développement.

**Important :** certaines étapes écrivent dans la base de données (générateur, ETL persist, analyse persist). Ne les lancez qu'après validation.

## 1. Prérequis

- Docker et Docker Compose (version récente)
- Python 3.10+ (interpréteur et `venv` pour l'environnement virtuel)
- `git` (pour cloner/committer)
- Client `psql` (optionnel, utile pour diagnostics)

Le backend Python dépend des paquets listés dans `backend/requirements.txt`.

## 2. Démarrage de l'infrastructure

Démarrer les services principaux définis dans `compose.yaml` :

```bash
# depuis la racine du dépôt
docker compose up -d postgres metabase_db metabase
```

Vérifier l'état des conteneurs et les logs Metabase :

```bash
docker compose ps
docker compose logs --tail=200 metabase
# vérifier que Postgres répond (exécute depuis l'hôte)
docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -c "SELECT 1"
```

Ports exposés utiles :

- Postgres application : hôte `localhost:5433` (container `hosfiital-postgres`)
- Metabase UI : http://localhost:3000 (container `hosfiital-metabase`)

## 3. Initialisation (première installation)

1. Installer les dépendances Python et créer un virtualenv :

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. Appliquer les migrations Alembic (crée le schéma DB) :

```bash
# depuis la racine du dépôt
python -m alembic -c backend/alembic.ini upgrade head
```

3. Déployer les vues BI (si présentes) dans la base :

```bash
# applique tous les fichiers SQL de backend/db/bi_views
cat backend/db/bi_views/*.sql | docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -v ON_ERROR_STOP=1
```

4. (Optionnel) Créer le rôle read-only attendu par Metabase. Voir la procédure complète dans `docs/PHASE5_DB_READONLY.md`.

5. Configurer Metabase via l'interface web (http://localhost:3000) :
   - Suivre l'assistant initial.
   - Ajouter la datasource PostgreSQL `hosfiital` : hôte `postgres` (depuis le conteneur Metabase) ou `127.0.0.1:5433` depuis l'hôte selon votre configuration.
   - Utiliser idéalement un compte read-only (`hosfiital_ro`) pour Metabase.

## 4. Alimenter les données (générateur)

Le projet fournit un générateur de données synthétiques : `scripts/generate_data.py`.

Exemple d'utilisation :

```bash
# génère 60 jours avec le scénario 'normal', démarrant le 2026-08-01, reset des données générées
python scripts/generate_data.py --scenario normal --days 60 --start-date 2026-08-01 --seed 42 --reset
```

Scénarios disponibles : `normal`, `saturation`, `budget_overrun`.
Paramètres principaux : `--days`, `--start-date`, `--seed`, `--reset`.

ATTENTION : cette commande écrit dans la base (`services`, `admissions`, `occupancy_snapshots`, `expenses`, `energy_consumption`, `staff_levels`, `service_capacity`, ...). Ne l'exécutez que si vous acceptez de modifier les données.

## 5. Pipeline ETL / KPI

Le calcul des KPI journaliers est fourni par `backend/app/etl/run_pipeline.py`.

Commande (exécute le calcul et retourne la liste des KPI) :

```bash
# calcul sans persistance
python -c "from backend.app.etl.run_pipeline import run_pipeline; print(run_pipeline())"

# calcul + persistance dans la table kpi_daily
python -c "from backend.app.etl.run_pipeline import run_pipeline; run_pipeline(persist=True)"
```

Rôle de `run_pipeline(..., persist=True)` : calcule les KPI (admissions, sorties, occupation, dépenses, énergie, capacité...) puis insère/actualise les lignes dans la table `kpi_daily` (INSERT ... ON CONFLICT DO UPDATE).

## 6. Analyse à la demande — point essentiel

Workflow attendu :

Données hospitalières → ETL/KPI → Analyse à la demande → `analyses` + `recommendations` → Metabase

L'analyse est déclenchée à la demande (pas d'automatisation programmée dans cette version).

Commandes possibles pour lancer une analyse et la persister :

1) Via l'API (si le backend FastAPI est démarré)

```bash
# démarrer l'API (depuis la racine du dépôt, avec l'environnement Python activé)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# déclencher une analyse via l'API (exemple pour la période août 2026)
curl -s -X POST http://localhost:8000/analyses -H 'Content-Type: application/json' -d '{"start":"2026-08-01","end":"2026-08-31"}' | jq
```

2) En ligne de commande Python (exécution directe, persist=True demande une session DB) :

```bash
python -c "from backend.app.db.session import SessionLocal; from backend.app.analysis.orchestrator import run_analysis; db=SessionLocal(); run_analysis(start=None,end=None,persist=True,db_session=db)"
```

Où sont stockés les résultats :

- Analyses : table `analyses` (JSONB `kpi_snapshot`, `anomalies`, `risk_level`)
- Recommandations : table `recommendations` (FK vers `analyses`, champs `text`, `type`, `status`)

Comment consulter :

- Directement en SQL via `psql` :
  - `SELECT * FROM analyses ORDER BY triggered_at DESC LIMIT 5;`
  - `SELECT * FROM recommendations WHERE created_at >= current_date - INTERVAL '30 days';`
- Via l'API (endpoints fournis) :
  - `POST /analyses` — exécute et persiste une analyse (voir plus haut)
  - `GET /analyses` — liste des analyses
  - `GET /analyses/{id}` — détail d'une analyse (inclut `recommendations`)

Visualisation dans Metabase : les vues `vw_recommendations` et autres `vw_*` sont exposées pour créer des cartes et dashboards. Importez ou créez des questions SQL qui interrogent les vues `vw_*`.

## 7. Workflow complet recommandé (très court)

1. `docker compose up -d postgres metabase_db metabase`
2. (optionnel) `python -m alembic -c backend/alembic.ini upgrade head` (si base vide)
3. `cat backend/db/bi_views/*.sql | docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -v ON_ERROR_STOP=1`
4. Générer ou recevoir les données hospitalières (`scripts/generate_data.py`) — écrit dans la base
5. Lancer le pipeline ETL/KPI (`run_pipeline(persist=True)`) — écrit dans `kpi_daily`
6. Lancer l'analyse à la demande (`run_analysis(..., persist=True)`) — écrit dans `analyses`/`recommendations`
7. Consulter résultats via API et Metabase

## 8. Arrêt / nettoyage

Arrêter les services (sans supprimer volumes) :

```bash
docker compose stop
```

Voir les logs (exemple Metabase) :

```bash
docker compose logs --tail=200 metabase
```

Arrêter et supprimer conteneurs (sans supprimer volumes) :

```bash
docker compose down
```

Supprimer volumes (déstructif) :

```bash
docker compose down -v
```

---

Fichiers et commandes cités dans ce guide :

- `compose.yaml` (services Postgres + Metabase)
- `backend/requirements.txt` (dépendances Python)
- `backend/alembic` (migrations)
- `backend/db/bi_views/*.sql` (vues BI)
- `scripts/generate_data.py` (générateur de données)
- `backend/app/etl/run_pipeline.py` (ETL / KPI)
- `backend/app/analysis/orchestrator.py` (analyse / recommandations)

Si vous voulez, je peux maintenant :
- committer ce guide (`docs/QUICKSTART.md`) dans Git (je m'en occupe si vous confirmez),
- ou modifier/compléter une section précise.
