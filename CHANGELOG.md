# Changelog

## Non publié

- Ajout de la pagination `?limit=` (1–100, défaut 50) et `?offset=` (≥ 0, défaut 0) sur `GET /athletes`, appliquée après le filtre `club` ; 422 si hors bornes.
- Ajout de `POST /athletes/import` : import du CSV de la fédération (`created`, `skipped`, `errors` par ligne ; 400 `invalid_csv` si CSV illisible). Suppression de `scripts/legacy/import_licencies.py`.
- Ajout de `GET /athletes/{athlete_id}` : détail d'un athlète (404 `not_found` si inconnu).
