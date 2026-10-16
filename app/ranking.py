from __future__ import annotations

import sqlite3

from app.schemas import RankingEntry, ResultUnit


def rank_results(rows: list[sqlite3.Row], unit: ResultUnit) -> list[RankingEntry]:
    """Classe les performances : temps croissants, distances et points décroissants.

    Les performances égales partagent le même rang et le rang suivant saute
    d'autant de places (classement 1, 2, 2, 4).
    """
    best_first = sorted(rows, key=lambda row: row["performance"], reverse=unit != ResultUnit.TIME_S)
    entries: list[RankingEntry] = []
    for position, row in enumerate(best_first, start=1):
        tied = entries and row["performance"] == entries[-1].performance
        entries.append(
            RankingEntry(
                rank=entries[-1].rank if tied else position,
                bib=row["bib"],
                athlete_id=row["athlete_id"],
                last_name=row["last_name"],
                first_name=row["first_name"],
                club=row["club"],
                performance=row["performance"],
            )
        )
    return entries
