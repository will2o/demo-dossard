# Changelog

## Non publié

- Ajout de `POST /athletes/import` : import du CSV de la fédération (`created`, `skipped`, `errors` par ligne ; 400 `invalid_csv` si CSV illisible). Suppression de `scripts/legacy/import_licencies.py`.
- Ajout de `GET /athletes/{athlete_id}` : détail d'un athlète (404 `not_found` si inconnu).
