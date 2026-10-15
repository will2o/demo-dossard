#!/usr/bin/env python3
"""Hook PreToolUse : bloque les commandes shell destructrices.

Lit le JSON de Claude Code sur l'entrée standard. Code de sortie 2 (message sur
la sortie d'erreur) si la commande Bash/PowerShell est jugée dangereuse, 0 sinon.
"""

import json
import re
import sys

OUTILS_SHELL = {"Bash", "PowerShell"}
SEPARATEURS = re.compile(r"[;&|\n]+")
SQL_DESTRUCTEUR = re.compile(r"\bDROP\s+(TABLE|VIEW)\b", re.IGNORECASE)


def _options(jetons: list[str]) -> tuple[set[str], set[str]]:
    """Retourne (lettres des options courtes, options longues) d'une liste de jetons."""
    courtes, longues = set(), set()
    for jeton in jetons:
        if jeton.startswith("--"):
            longues.add(jeton.split("=", 1)[0])
        elif jeton.startswith("-") and len(jeton) > 1:
            courtes.update(jeton[1:])
    return courtes, longues


def _jetons_apres(segment: str, motif: str) -> list[str] | None:
    """Jetons suivant la première occurrence de `motif` dans le segment, ou None."""
    correspondance = re.search(motif, segment)
    if not correspondance:
        return None
    return segment[correspondance.end() :].split()


def raison_blocage(commande: str) -> str | None:
    """Retourne la raison du blocage, ou None si la commande est acceptable."""
    if SQL_DESTRUCTEUR.search(commande):
        return "suppression SQL (DROP TABLE / DROP VIEW)"

    for segment in SEPARATEURS.split(commande):
        jetons = _jetons_apres(segment, r"(?:^|\s)rm(?=\s)")
        if jetons is not None:
            courtes, longues = _options(jetons)
            recursif = bool(courtes & {"r", "R"}) or "--recursive" in longues
            force = "f" in courtes or "--force" in longues
            if recursif and force:
                return "suppression récursive forcée (rm -rf)"

        jetons = _jetons_apres(segment, r"(?:^|\s)git\s+(?:\S+\s+)*?push(?=\s|$)")
        if jetons is not None:
            courtes, longues = _options(jetons)
            if "f" in courtes or "--force" in longues:
                return "push forcé (git push --force)"

    return None


def main() -> int:
    try:
        donnees = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    if donnees.get("tool_name") not in OUTILS_SHELL:
        return 0

    commande = (donnees.get("tool_input") or {}).get("command")
    if not isinstance(commande, str):
        return 0

    raison = raison_blocage(commande)
    if raison:
        print(f"Bloqué par le hook garde.py : {raison}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
