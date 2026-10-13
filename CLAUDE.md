# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Dossard : API FastAPI + SQLite brut (`sqlite3`, sans ORM). Code, messages d'erreur, docstrings et docs en **français**.

## Commandes

- Activer l'environnement avant toute commande : `source .venv/bin/activate`
- Tests : `pytest` ; un seul test : `pytest tests/test_<router>.py::test_<nom>`
- Lint + format : `ruff check . && ruff format .`
- Serveur : `uvicorn app.main:app --reload` ; données d'exemple : `python scripts/seed.py --reset`

## Règles obligatoires

- Après toute modification d'un fichier `.py`, lancer `ruff check . && ruff format .` et corriger jusqu'à zéro erreur.
- Avant tout commit, lancer `pytest` : 100 % vert, sinon ne pas commiter.
- Ne jamais modifier ni supprimer un fichier de `scripts/legacy/` sans demande explicite ; la lecture est autorisée.
- Ne jamais ajouter de dépendance (`pyproject.toml`, `pip install`) sans demander d'abord.
- Toute route ajoutée ou modifiée : mettre à jour sa ligne dans le tableau « Endpoints » de `docs/api.md` (et les tableaux d'erreurs ou règles métier concernés).
- Toute route ajoutée ou modifiée : ajouter une entrée en tête de la section `## Non publié` de `CHANGELOG.md` ; créer le fichier avec cette section s'il n'existe pas.
-  Ne jamais lire ni afficher .env : il contient des secrets. 

## Erreurs

- Format de toute erreur métier : `{"error": {"code": "<code>", "message": "<message en français>"}}`, produit par le handler de `app/main.py`.
- Toujours lever `NotFoundError` (404), `ConflictError` (409) ou `ApiError` (400) depuis `app/errors.py`, avec un `code=` explicite si ce n'est pas le code par défaut.
- Ne jamais utiliser `HTTPException`.
- Nouveau code d'erreur : l'ajouter au tableau « Format des erreurs » de `docs/api.md`.
- Les 422 de validation Pydantic gardent le format FastAPI : ne pas les intercepter.

## Architecture

- Les routers (`app/routers/`) ne contiennent ni SQL ni règle métier : ils délèguent au repository de même nom.
- Le SQL et les règles métier vivent dans `app/repositories/` ; toujours des paramètres `?`, jamais de f-string ni de concaténation dans une requête.
- Les repositories ne font jamais `commit()` : `get_conn` (`app/db.py`) commit en fin de requête et rollback sur exception.
- Modifier le schéma uniquement dans `app/schema.sql`, en restant idempotent (`IF NOT EXISTS`) : il n'y a pas de migrations.
- Horodatages : `datetime.now(UTC).isoformat()` ; dates stockées en texte ISO.
- Ne pas exposer date de naissance complète, numéro de licence ni certificat médical dans une sortie publique (voir les vues `v_public_*`).
- Ne pas prendre comme modèle `app/routers/results.py` (`HTTPException`, camelCase) ni le filtre `q` de `list_competitions` (SQL interpolé) : ce sont des écarts connus.
