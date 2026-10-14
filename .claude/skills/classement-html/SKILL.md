---
name: classement-html
description: Génère une page HTML (un fichier) du classement d'une épreuve de dossard. À utiliser quand on demande le classement d'une épreuve en HTML, une page ou un fichier HTML des résultats.
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/classement_html.py *)
---

# Classement d'une épreuve en HTML

Le HTML est produit uniquement par le script : ne jamais écrire ni modifier de HTML à la main.

1. Si l'identifiant de l'épreuve (`event_id`) n'est pas donné, le chercher dans `data/dossard.db` (table `events`, colonnes `id`, `name`, `unit`) à partir du nom ou de la compétition indiqués. S'il reste ambigu, demander lequel choisir.
2. Lancer, depuis la racine du dépôt (venv activé) :
   `python ${CLAUDE_SKILL_DIR}/scripts/classement_html.py <event_id>`
3. En cas d'erreur du script (base ou épreuve introuvable, classement indisponible), rapporter le message tel quel sans contourner le script.
4. Donner à l'utilisateur le chemin du fichier produit (`classement-<event_id>.html`, à la racine du dépôt) et le nombre d'athlètes classés affichés par le script.
