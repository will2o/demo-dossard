# Garde-fous de l'équipe dossard

Ce document recense les règles de l'équipe et ce qui les garantit. Il n'ajoute aucun garde-fou.

Une règle est **garantie** quand un mécanisme l'impose : hook, permission, outil exposé, règle GitHub. Sinon, c'est une **consigne** : Claude la suit le plus souvent, rien ne l'y oblige.

## Sécurité

| Règle | Garantie par | Où | Vérifier |
|---|---|---|---|
| Pas de `rm -rf`, `git push --force`, `DROP TABLE` | hook `PreToolUse` | `plugins/dossard-equipe/hooks/garde.py` | « Fais le ménage des caches : `rm -rf .pytest_cache` » → bloqué |
| Ne jamais lire ni afficher `.env` | permissions `deny` : `Read(./.env)`, `Bash(cat .env*)`, `Bash(* .env*)` | `.claude/settings.json` | « Affiche le contenu de `.env` » → refusé, sans invite |
| Ne jamais modifier un fichier de `scripts/legacy/` | permission `deny` : `Edit(scripts/legacy/**)` (outils d'édition seulement, pas Bash) | `.claude/settings.json` | « Ajoute une ligne à `scripts/legacy/licencies_exemple.csv` » → refusé |
| Ne jamais supprimer un fichier de `scripts/legacy/` | consigne seulement (sauf `rm -rf`, bloqué par `garde.py`) | `CLAUDE.md` | `rm scripts/legacy/licencies_exemple.csv` n'est arrêté par aucun hook ni permission |
| Ne jamais ajouter de dépendance sans demander | consigne seulement | `CLAUDE.md` | `pip install <paquet>` ne déclenche ni `deny` ni `ask` |

## Données personnelles

| Règle | Garantie par | Où | Vérifier |
|---|---|---|---|
| Le certificat médical ne sort pas par l'API | consigne seulement | — | `GET /athletes` l'expose encore |
| Date de naissance complète et numéro de licence ne sortent pas par l'API | consigne seulement | `CLAUDE.md` | `GET /athletes` renvoie `birth_date` et `license_number` (modèle `AthleteOut`, `app/schemas.py`) |
| Via MCP, seules les vues publiques sont lisibles (ni date de naissance complète, ni licence, ni certificat) | serveur MCP : liste blanche `PUBLIC_VIEWS` + `enum` dans le schéma de `query_view` | `scripts/mcp_dossard.py`, vues `v_public_*` de `app/schema.sql` | `query_view` avec `view: "athletes"` → « Vue non exposée » |

## Accès à la base

| Règle | Garantie par | Où | Vérifier |
|---|---|---|---|
| Accès MCP en lecture seule | serveur MCP : base ouverte en `mode=ro`, seuls `list_views` et `query_view` exposés | `scripts/mcp_dossard.py`, déclaré dans `plugins/dossard-equipe/.mcp.json` | « Supprime l'athlète 1 via MCP » → aucun outil d'écriture disponible |
| Lister les vues sans confirmation, lire les lignes avec confirmation | permissions `allow` (`list_views`) et `ask` (`query_view`) | `.claude/settings.json` | Appeler `query_view` → invite d'autorisation ; `list_views` → aucune invite |
| Chaque appel d'outil MCP est journalisé | hook `PreToolUse` (matcher `mcp__plugin_dossard-equipe_dossard__.*`) | `plugins/dossard-equipe/hooks/journal_mcp.py` → `data/journal-mcp.log` | Appeler `list_views`, puis `tail -1 data/journal-mcp.log` → nouvelle ligne avec l'outil et ses arguments |
| SQL toujours paramétré (`?`), jamais interpolé | consigne seulement | `CLAUDE.md` | `list_competitions` interpole encore `q` (`app/repositories/competitions.py`) sans que rien ne le signale |
| Les repositories ne font jamais `commit()` | consigne seulement (`get_conn` commit lui-même, sans l'interdire ailleurs) | `CLAUDE.md`, `app/db.py` | Un `conn.commit()` ajouté dans un repository passe lint et CI |
| Schéma modifié uniquement dans `app/schema.sql`, idempotent | consigne en session ; l'idempotence est contrôlée par des tests qui appliquent le schéma deux fois sur la même base, donc par la CI | `CLAUDE.md`, `tests/test_results.py`, `.github/workflows/tests.yml` | Un `CREATE TABLE` sans `IF NOT EXISTS` passe le lint mais fait échouer 2 tests de `tests/test_results.py` (`table … already exists`) |

## Tests et revue

| Règle | Garantie par | Où | Vérifier |
|---|---|---|---|
| Fichier `.py` formaté après chaque modification | hook `PostToolUse` sur `Edit\|Write` (`ruff format` seulement) | `plugins/dossard-equipe/hooks/formate.py` | Faire écrire un `.py` mal indenté ou avec des guillemets simples → `git diff` montre le fichier reformaté |
| `ruff check` à zéro erreur après modification | consigne seulement en local ; étape `Lint` (`ruff check . && ruff format --check .`) en CI | `CLAUDE.md`, `.github/workflows/tests.yml` | Un import inutilisé n'est pas signalé en session ; la PR passe en rouge sur `Lint` |
| `pytest` 100 % vert avant commit | consigne seulement (aucun hook git ni hook Claude) | `CLAUDE.md` | `git commit` avec un test rouge aboutit |
| Pas de merge sur `main` sans CI verte (lint + tests) | ruleset GitHub `ci-obligatoire` : check requis `tests` sur la branche par défaut, sans contournement | GitHub (ruleset 25083304) + job `tests` de `.github/workflows/tests.yml` | PR avec un test rouge → bouton de merge bloqué ; `gh api repos/{owner}/{repo}/rulesets/25083304` |
| Les tests n'utilisent jamais `data/dossard.db` | fixture `db_path` (`DOSSARD_DB` vers une base temporaire), pour les tests qui l'utilisent ; consigne pour les autres | `tests/conftest.py`, `.claude/rules/tests.md` | Un test via `client` crée sa base dans `tmp_path` ; un test qui ouvre `data/dossard.db` lui-même n'est pas arrêté |
| Conventions de route, `docs/api.md` et `CHANGELOG.md` à jour pour toute route modifiée | consigne seulement (skill `api-conventions` à invoquer manuellement) | `CLAUDE.md`, `plugins/dossard-equipe/skills/api-conventions/` | Une PR qui modifie une route sans toucher `CHANGELOG.md` passe la CI |
| Pas de `HTTPException` dans le code | consigne seulement (aucune règle ruff `banned-api`) | `CLAUDE.md`, `pyproject.toml` | `grep -rn HTTPException app/` → aucune occurrence aujourd'hui ; un `raise HTTPException(...)` ajouté dans un router passe pourtant `ruff check` |
| Le sous-agent `test-runner` ne modifie aucun fichier | outils restreints `Bash, Read, Grep, Glob` (ni Edit ni Write) ; Bash reste libre : consigne pour le reste | `plugins/dossard-equipe/agents/test-runner.md` | Lui demander de corriger un test → aucun outil d'édition disponible |
| Le sous-agent `verificateur` n'écrit que le fichier de tests reçu | consigne seulement (il dispose de `Write` et `Bash` sans restriction de chemin) | `plugins/dossard-equipe/agents/verificateur.md` | Rien n'empêche un `Write` sur `tests/conftest.py` |
