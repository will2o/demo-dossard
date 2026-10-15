"""Serveur MCP de dossard : lecture seule, vues publiques uniquement.

Usage (lancé par Claude Code, pas à la main) :
    python scripts/mcp_dossard.py

Transport stdio : un message JSON-RPC 2.0 par ligne sur stdin, une réponse par ligne sur stdout.
Journal sur stderr. Bibliothèque standard uniquement.

Deux garde-fous dans le serveur lui-même :
- la base est ouverte en lecture seule (URI SQLite `mode=ro`) ;
- seules les vues de PUBLIC_VIEWS sont interrogeables, avec des filtres d'égalité sur leurs
  colonnes : aucune requête SQL libre, aucune table.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Any

SERVER_INFO = {"name": "dossard", "version": "1.0.0"}
SUPPORTED_VERSIONS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
PUBLIC_VIEWS = ("v_public_athletes", "v_public_results")
MAX_LIMIT = 200

TOOLS = [
    {
        "name": "list_views",
        "description": "Liste les vues publiques de la base dossard et leurs colonnes.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "query_view",
        "description": (
            "Lit les lignes d'une vue publique de dossard. Filtres d'égalité exacte sur les "
            f"colonnes de la vue. Au plus {MAX_LIMIT} lignes par appel."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "view": {"type": "string", "enum": list(PUBLIC_VIEWS)},
                "filters": {
                    "type": "object",
                    "description": "Colonne -> valeur attendue (égalité exacte).",
                    "additionalProperties": {"type": ["string", "number", "integer"]},
                },
                "limit": {"type": "integer", "minimum": 1, "maximum": MAX_LIMIT, "default": 50},
                "offset": {"type": "integer", "minimum": 0, "default": 0},
            },
            "required": ["view"],
        },
    },
]


def db_path() -> Path:
    """Même règle que app/db.py : DOSSARD_DB, sinon data/dossard.db à la racine du dépôt."""
    env = os.environ.get("DOSSARD_DB")
    return Path(env) if env else Path(__file__).resolve().parent.parent / "data" / "dossard.db"


def connect_read_only() -> sqlite3.Connection:
    path = db_path()
    if not path.exists():
        raise ToolError(f"Base introuvable : {path}. Lancez d'abord python scripts/seed.py.")
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


class ToolError(Exception):
    """Erreur renvoyée à Claude comme résultat d'outil (isError), pas comme erreur JSON-RPC."""


def view_columns(conn: sqlite3.Connection, view: str) -> list[str]:
    return [row["name"] for row in conn.execute(f"PRAGMA table_info({view})")]


def list_views(_: dict[str, Any]) -> Any:
    with connect_read_only() as conn:
        return {view: view_columns(conn, view) for view in PUBLIC_VIEWS}


def query_view(args: dict[str, Any]) -> Any:
    view = args.get("view")
    if view not in PUBLIC_VIEWS:
        raise ToolError(
            f"Vue non exposée : {view!r}. Vues disponibles : {', '.join(PUBLIC_VIEWS)}."
        )
    filters = args.get("filters") or {}
    limit = min(int(args.get("limit", 50)), MAX_LIMIT)
    offset = max(int(args.get("offset", 0)), 0)
    with connect_read_only() as conn:
        columns = view_columns(conn, view)
        unknown = [name for name in filters if name not in columns]
        if unknown:
            raise ToolError(
                f"Colonne(s) absente(s) de {view} : {', '.join(unknown)}. "
                f"Colonnes disponibles : {', '.join(columns)}."
            )
        where = " AND ".join(f"{name} = ?" for name in filters) or "1"
        sql = f"SELECT * FROM {view} WHERE {where} LIMIT ? OFFSET ?"
        rows = conn.execute(sql, [*filters.values(), limit, offset]).fetchall()
    return {"view": view, "count": len(rows), "rows": [dict(row) for row in rows]}


HANDLERS = {"list_views": list_views, "query_view": query_view}


def call_tool(params: dict[str, Any]) -> dict[str, Any]:
    name = params.get("name")
    handler = HANDLERS.get(name)
    if handler is None:
        return text_result(f"Outil inconnu : {name}", is_error=True)
    try:
        payload = handler(params.get("arguments") or {})
    except ToolError as exc:
        return text_result(str(exc), is_error=True)
    except sqlite3.Error as exc:
        return text_result(f"Erreur SQLite : {exc}", is_error=True)
    return text_result(json.dumps(payload, ensure_ascii=False, default=str))


def text_result(text: str, *, is_error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    method = message.get("method")
    params = message.get("params") or {}
    if "id" not in message:  # notification (notifications/initialized…) : pas de réponse
        return None
    if method == "initialize":
        asked = params.get("protocolVersion")
        result: Any = {
            "protocolVersion": asked if asked in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0],
            "capabilities": {"tools": {}},
            "serverInfo": SERVER_INFO,
        }
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        result = call_tool(params)
    else:
        return {
            "jsonrpc": "2.0",
            "id": message["id"],
            "error": {"code": -32601, "message": f"Méthode inconnue : {method}"},
        }
    return {"jsonrpc": "2.0", "id": message["id"], "result": result}


def main() -> None:
    # Windows : stdin et stdout ne sont pas en UTF-8 par défaut.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    print(f"mcp_dossard : base {db_path()} (lecture seule)", file=sys.stderr)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(message)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
