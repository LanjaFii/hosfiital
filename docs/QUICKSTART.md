# QUICKSTART — Hosfiital (fiche de démarrage)

Ce guide court décrit comment démarrer l'infrastructure, initialiser la base, générer des données, lancer le pipeline ETL/KPI, exécuter une analyse à la demande et visualiser le tout dans Metabase. Chaque étape est expliquée simplement, comme à une personne qui ne fait pas d'informatique.

**Important :** certaines étapes écrivent dans la base de données (générateur, ETL persist, analyse persist). Ne les lancez qu'après validation.

---

## 1. Prérequis — ce qu'il faut avoir installé avant de commencer

- **Docker et Docker Compose** (version récente) : permet de lancer Postgres et Metabase comme des « boîtes » prêtes à l'emploi, sans rien installer d'autre sur la machine.
- **Python 3.10+** avec un environnement virtuel (`venv`) : pour exécuter le code du projet (génération de données, calcul des indicateurs).
- **`git`** : pour récupérer et garder l'historique du code.
- **Client `psql`** (optionnel mais pratique) : permet de « regarder » directement dans la base de données pour vérifier/utiliser les données.

Le backend Python dépend des paquets listés dans `backend/requirements.txt` (installés plus bas à l'étape 3).

---

## 2. Démarrage de l'infrastructure — « allumer » les services

On démarre les trois services définis dans `compose.yaml` :
- **Postgres** : le « classeur » où sont rangées toutes les données de l'hôpital.
- **metabase_db** : le « classeur interne » de Metabase (où Metabase mémorise ses propres réglages).
- **metabase** : l'application qui affiche les tableaux de bord dans un navigateur.

```bash
# depuis la racine du dépôt
docker compose up -d postgres metabase_db metabase
```

Vérifier que tout est bien lancé et consulter les journaux de Metabase :

```bash
docker compose ps
docker compose logs --tail=200 metabase
# vérifier que Postgres répond (exécute depuis l'hôte)
docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -c "SELECT 1"
```

Ports exposés utiles (par où on accède aux services) :

- Postgres application : hôte `localhost:5433` (container `hosfiital-postgres`)
- Metabase UI : http://localhost:3000 (container `hosfiital-metabase`)

---

## 3. Initialisation — « préparer le classeur » (première installation uniquement)

À ne faire qu'une fois, à la toute première installation.

1. **Installer les dépendances Python et créer l'environnement virtuel** — c'est comme préparer la « caisse à outils » du projet :

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

2. **Appliquer les migrations Alembic** — cela crée le plan de la base de données (les « étagères » du classeur, c'est-à-dire les tables) :

```bash
# depuis la racine du dépôt
python -m alembic -c backend/alembic.ini upgrade head
```

3. **Déployer les vues BI** — ce sont des « fenêtres de lecture toute prêtes » que les tableaux de bord Metabase utilisent pour consulter les données de façon cohérente :

```bash
# applique tous les fichiers SQL de backend/db/bi_views
cat backend/db/bi_views/*.sql | docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -v ON_ERROR_STOP=1
```

4. **(Optionnel) Créer le rôle en lecture seule attendu par Metabase** — un compte qui peut *voir* les données mais pas les modifier, pour la sécurité. Voir la procédure complète dans `docs/PHASE5_DB_READONLY.md`.

5. **Configurer Metabase via l'interface web** (http://localhost:3000) — c'est comme « connecter Metabase au classeur » :
   - Suivre l'assistant initial.
   - Ajouter la datasource PostgreSQL `hosfiital` : hôte `postgres` (depuis le conteneur Metabase) ou `127.0.0.1:5433` depuis l'hôte selon votre configuration.
   - Utiliser idéalement un compte en lecture seule (`hosfiital_ro`) pour Metabase.

6. **(Optionnel mais recommandé) Importer les tableaux de bord prêts à l'emploi** — des modèles de dashboards (`A`, `C`, `G`) sont fournis dans `backend/db/metabase_exports` ; un petit script permet de les créer dans votre Metabase en un clic. La procédure complète est dans `docs/IMPORT_METABASE.md` :

```bash
METABASE_URL=http://localhost:3000 \
  METABASE_USER=you@example.com METABASE_PASSWORD=secret \
  python backend/tools/import_metabase_dashboards.py --path backend/db/metabase_exports
```

---

## 4. Alimenter les données (générateur) — « remplir le classeur »

Le projet fournit un générateur de **données synthétiques** (simulées mais réalistes) : `scripts/generate_data.py`. Ça permet de tester les tableaux de bord sans avoir de vrais patients.

Exemple d'utilisation :

```bash
# génère 60 jours avec le scénario 'normal', démarrant le 2026-08-01, en effaçant d'abord l'ancien contenu
python scripts/generate_data.py --scenario normal --days 60 --start-date 2026-08-01 --seed 42 --reset
```

Scénarios disponibles :
- `normal` : activité « classique » d'un hôpital.
- `saturation` : l'hôpital se remplit de plus en plus (pour tester les alertes de capacité).
- `budget_overrun` : les dépenses dépassent le budget (pour tester les alertes financières).

Paramètres principaux : `--days` (nombre de jours), `--start-date` (date de début), `--seed` (graine → mêmes résultats à chaque fois pour reproductibilité), `--reset` (vide les tables avant de réécrire : utile pour repartir propre).

> **Astuce importante :** utilisez `--reset` quand vous régénérez les données. Cela vide aussi la table `kpi_daily` (les indicateurs journaliers calculés) afin qu'il n'en reste pas des valeurs périmées d'une ancienne simulation qui fausseraient les dashboards.

ATTENTION : cette commande écrit dans la base (`services`, `admissions`, `occupancy_snapshots`, `expenses`, `energy_consumption`, `staff_levels`, `service_capacity`, ...). Ne l'exécutez que si vous acceptez de modifier les données.

---

## 5. Pipeline ETL / KPI — « calculer les indicateurs du jour »

Le générateur fournit des données « brutes » (qui est arrivé, combien de lits occupés, combien dépensé...). Pour que les tableaux de bord aient des chiffres synthétiques par jour, il faut **calculer ces indicateurs** et les enregistrer dans la table `kpi_daily`. Sans cette étape, les dashboards (et surtout la vue « dernier jour ») afficheraient des zéros dès qu'on régénère les données.

Le calcul est fourni par `backend/app/etl/run_pipeline.py`.

Commande (exécute le calcul et retourne la liste des KPI) :

```bash
# calcul sans l'enregistrer
python -c "from backend.app.etl.run_pipeline import run_pipeline; print(run_pipeline())"

# calcul + enregistrement dans la table kpi_daily (obligatoire après avoir généré des données)
python -c "from backend.app.etl.run_pipeline import run_pipeline; run_pipeline(persist=True)"
```

**Pourquoi c'est nécessaire :** le tableau de bord se base sur `kpi_daily` pour définir telle plage de dates (par ex. le « dernier jour »), et pour afficher les séries jour par jour. Si cette table n'est pas à jour par rapport aux données générées, les cartes du dashboard montrent des valeurs manquantes ou à zéro. **Il faut donc toujours relancer cette étape après avoir régénéré les données.**

---

## 6. Analyse à la demande — « faire expertiser l'hôpital »

Workflow attendu :

```
Données hospitalières → ETL/KPI → Analyse à la demande → analyses + recommendations → Metabase
```

L'analyse est un « contrôle de santé » automatisé : un moteur de règles parcourt les indicateurs et signale les anomalies éventuelles (capacité saturée, budget dépassé...) sous forme de **recommandations**. Elle est déclenchée **à la demande** (pas d'automatisation programmée dans cette version).

Commandes possibles pour lancer une analyse et l'enregistrer :

1) **Via l'API** (si le backend FastAPI est démarré) — pratique depuis un navigateur ou un outil :

```bash
# démarrer l'API (depuis la racine du dépôt, avec l'environnement Python activé)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# déclencher une analyse via l'API (exemple pour la période août 2026)
curl -s -X POST http://localhost:8000/analyses -H 'Content-Type: application/json' -d '{"start":"2026-08-01","end":"2026-08-31"}' | jq
```

2) **En ligne de commande Python** (exécution directe ; `persist=True` demande une session DB) :

```bash
python -c "from backend.app.db.session import SessionLocal; from backend.app.analysis.orchestrator import run_analysis; db=SessionLocal(); run_analysis(start=None,end=None,persist=True,db_session=db)"
```

Où sont stockés les résultats :

- **Analyses** : table `analyses` (JSONB `kpi_snapshot`, `anomalies`, `risk_level`) → le « bilan » complet.
- **Recommandations** : table `recommendations` (lien vers l'analyse, champs `text`, `type`, `status`) → les actions conseillées.

Comment consulter les résultats :

- **Directement en SQL via `psql`** :
  - `SELECT * FROM analyses ORDER BY triggered_at DESC LIMIT 5;`
  - `SELECT * FROM recommendations WHERE created_at >= current_date - INTERVAL '30 days';`
- **Via l'API** (endpoints fournis) :
  - `POST /analyses` — exécute et enregistre une analyse (voir plus haut)
  - `GET /analyses` — liste des analyses
  - `GET /analyses/{id}` — détail d'une analyse (inclut ses `recommendations`)
  - `PATCH /recommendations/{id}` — changer le statut d'une recommandation (`accepted`, `rejected`, `open`)

Visualisation dans Metabase : les vues `vw_recommendations` et autres `vw_*` sont exposées pour créer des cartes et dashboards. Importez ou créez des questions SQL qui interrogent les vues `vw_*`.

---

## 7. Workflow complet recommandé (très court) — la « recette » d'ensemble

Pour repartir de zéro et avoir un dashboard qui tourne :

1. `docker compose up -d postgres metabase_db metabase` — allumer les services.
2. (optionnel) `python -m alembic -c backend/alembic.ini upgrade head` — créer les tables (si base vide).
3. `cat backend/db/bi_views/*.sql | docker exec -i hosfiital-postgres psql -U hosfiital -d hosfiital -v ON_ERROR_STOP=1` — créer les vues de lecture pour Metabase.
4. Générer ou recevoir les données hospitalières (`scripts/generate_data.py --reset`) — remplir le classeur.
5. Lancer le pipeline ETL/KPI (`run_pipeline(persist=True)`) — **indispensable** pour calculer et enregistrer les indicateurs journaliers (`kpi_daily`).
6. Lancer l'analyse à la demande (`run_analysis(..., persist=True)`) — faire le bilan/les recommandations (`analyses`/`recommendations`).
7. (optionnel) Importer les tableaux de bord Metabase (`backend/tools/import_metabase_dashboards.py`) — créer les dashboards A, C, G.
8. Consulter les résultats via l'API et Metabase — regarder le résultat.

---

## 8. Arrêt / nettoyage — « éteindre ou ranger »

Arrêter les services (sans supprimer les données) :

```bash
docker compose stop
```

Voir les journaux (exemple Metabase) :

```bash
docker compose logs --tail=200 metabase
```

Arrêter et supprimer les conteneurs (sans supprimer les données) :

```bash
docker compose down
```

**Supprimer aussi les volumes (destructif — efface définitivement toutes les données) :**

```bash
docker compose down -v
```

---

## Fichiers et commandes cités dans ce guide

- `compose.yaml` — définit les services (Postgres + Metabase).
- `backend/requirements.txt` — dépendances Python.
- `backend/alembic` — migrations (création/mise à jour du schéma DB).
- `backend/db/bi_views/*.sql` — vues BI (fenêtres de lecture pour les dashboards).
- `backend/db/metabase_exports/` — exports JSON des dashboards A, C, G prêts à l'emploi.
- `backend/tools/import_metabase_dashboards.py` — script pour importer ces dashboards dans Metabase (voir `docs/IMPORT_METABASE.md`).
- `scripts/generate_data.py` — générateur de données simulées.
- `backend/app/etl/run_pipeline.py` — calcul des KPI journaliers (`kpi_daily`).
- `backend/app/analysis/orchestrator.py` — analyse / recommandations.
