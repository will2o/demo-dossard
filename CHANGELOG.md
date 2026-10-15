# Changelog

## Non publié

- Ajout de `GET /competitions/{competition_id}/stats` : nombre d'épreuves, d'inscriptions confirmées et de résultats de la compétition (404 `not_found` si inconnue).
- Correction de `GET /competitions/{competition_id}/results.csv` : les champs contenant une virgule (ex. nom de club) sont désormais entre guillemets, ce qui ne décale plus les colonnes.
- Harmonisation du router des résultats : `GET /events/{event_id}/ranking` renvoie désormais la liste nue (plus d'enveloppe `{"data", "count"}`) et son 404 passe au format `{"error": …}` (`not_found`) ; ajout des `summary` sur les trois routes.
- Ajout de la pagination `?limit=` (1–100, défaut 50) et `?offset=` (≥ 0, défaut 0) sur `GET /athletes`, appliquée après le filtre `club` ; 422 si hors bornes.
- Ajout de `POST /athletes/import` : import du CSV de la fédération (`created`, `skipped`, `errors` par ligne ; 400 `invalid_csv` si CSV illisible). Suppression de `scripts/legacy/import_licencies.py`.
- Ajout de `GET /athletes/{athlete_id}` : détail d'un athlète (404 `not_found` si inconnu).
