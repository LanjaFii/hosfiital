# Importer les dashboards Metabase

Ce document explique comment ré-importer les dashboards Metabase stockés dans `backend/db/metabase_exports` vers une instance Metabase via l'API.

Prérequis
- Metabase démarré et accessible (par défaut http://localhost:3000).
- Un compte Metabase (email/mot de passe) ou un token API.
- Le projet contient des exports JSON dans `backend/db/metabase_exports` (fourni).
- `httpx` est une dépendance présente dans `backend/requirements.txt`.

Variables d'environnement
- `METABASE_URL` (optionnel, défaut `http://localhost:3000`)
- `METABASE_USER` et `METABASE_PASSWORD` (ou `METABASE_API_TOKEN`)

Script
- Fichier : `backend/tools/import_metabase_dashboards.py`
- Usage simple (login) :

```bash
METABASE_URL=http://localhost:3000 \
  METABASE_USER=you@example.com METABASE_PASSWORD=secret \
  python backend/tools/import_metabase_dashboards.py --path backend/db/metabase_exports
```

- Option `--dry-run` pour simuler les actions sans créer d'objets :

```bash
METABASE_API_TOKEN=... python backend/tools/import_metabase_dashboards.py --dry-run
```

Comportement
- Pour chaque fichier JSON dans le dossier d'export, le script :
  - crée les `cards` (questions) décrites,
  - crée le `dashboard`,
  - ajoute les cartes au dashboard avec une mise en grille simple.

Remarques et risques
- Le script utilise l'API publique de Metabase ; les imports peuvent créer des doublons si vous l'exécutez plusieurs fois.
- Si vous préférez restaurer l'état exact d'une ancienne instance Metabase, utilisez un dump/restore du metadata DB (Postgres/H2) plutôt que l'API.
- Vérifiez que l'ID de la datasource (`database_id`) référencé dans les exports correspond bien à votre instance (sinon adaptez manuellement les exports avant import).

Si vous voulez, je peux :
- exécuter un `--dry-run` localement (si vous fournissez l'URL et les identifiants),
- ou lancer l'import réel si vous confirmez.
