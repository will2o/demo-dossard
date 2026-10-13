---
paths:
  - "tests/**"
---

# Tests

- Un fichier `tests/test_<router>.py` par router ; y ajouter les tests de toute route nouvelle ou modifiée.
- Créer les données via les fixtures de `tests/conftest.py` : `client`, `make_competition(status=...)`, `make_event`, `make_athlete`, `make_registration(confirm=...)` ; ne pas écrire de SQL ni de fixture équivalente dans les tests.
- Pour chaque route, tester le cas nominal **et** chaque cas d'erreur applicable : 404, 409 (en vérifiant `response.json()["error"]["code"]`), 422.
- Dates relatives à `date.today()`, jamais codées en dur.
- Ne jamais utiliser `data/dossard.db` dans un test (la fixture `db_path` fournit une base temporaire via `DOSSARD_DB`).
