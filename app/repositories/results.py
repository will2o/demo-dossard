from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from app.errors import ConflictError, NotFoundError
from app.ranking import rank_results
from app.schemas import RankingEntry, ResultOut, ResultUnit


def record_result(conn: sqlite3.Connection, registration_id: int, performance: float) -> ResultOut:
    registration = conn.execute(
        "SELECT r.id, r.status, c.status AS competition_status"
        " FROM registrations r"
        " JOIN events e ON e.id = r.event_id"
        " JOIN competitions c ON c.id = e.competition_id"
        " WHERE r.id = ?",
        (registration_id,),
    ).fetchone()
    if registration is None:
        raise NotFoundError(f"Inscription {registration_id} introuvable")
    if registration["status"] != "confirmed" or registration["competition_status"] != "closed":
        raise ConflictError(
            "Résultat possible seulement sur une inscription confirmée d'une compétition close",
            code="results_not_allowed",
        )

    recorded_at = datetime.now(UTC)
    conn.execute(
        "INSERT INTO results (registration_id, performance, recorded_at) VALUES (?, ?, ?)"
        " ON CONFLICT (registration_id) DO UPDATE"
        " SET performance = excluded.performance, recorded_at = excluded.recorded_at",
        (registration_id, performance, recorded_at.isoformat()),
    )
    return ResultOut(
        registration_id=registration_id, performance=performance, recorded_at=recorded_at
    )


def get_ranking(conn: sqlite3.Connection, event_id: int) -> list[RankingEntry]:
    event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if event is None:
        raise NotFoundError(f"Épreuve {event_id} introuvable")
    return rank_results(ranking_rows(conn, event_id), ResultUnit(event["unit"]))


def ranking_rows(conn: sqlite3.Connection, event_id: int) -> list[sqlite3.Row]:
    """Inscriptions confirmées de l'épreuve qui ont un résultat."""
    return conn.execute(
        "SELECT r.bib, r.athlete_id, a.last_name, a.first_name, a.club, res.performance"
        " FROM results res"
        " JOIN registrations r ON r.id = res.registration_id"
        " JOIN athletes a ON a.id = r.athlete_id"
        " WHERE r.event_id = ? AND r.status = 'confirmed'"
        " ORDER BY r.bib",
        (event_id,),
    ).fetchall()


def export_csv(conn: sqlite3.Connection, competition_id: int) -> str:
    competition = conn.execute(
        "SELECT * FROM competitions WHERE id = ?", (competition_id,)
    ).fetchone()
    if competition is None:
        raise NotFoundError(f"Compétition {competition_id} introuvable")

    lines = []
    lines.append(
        "competition,event,unit,bib,first_name,last_name,birth_date,sex,club,"
        "license_number,medical_certificate_valid_until,performance"
    )
    events = conn.execute(
        "SELECT * FROM events WHERE competition_id = ? ORDER BY id", (competition_id,)
    ).fetchall()
    for event in events:
        rows = conn.execute(
            "SELECT r.bib, a.*, res.performance FROM results res"
            " JOIN registrations r ON r.id = res.registration_id"
            " JOIN athletes a ON a.id = r.athlete_id"
            " WHERE r.event_id = ? AND r.status = 'confirmed' ORDER BY r.bib",
            (event["id"],),
        ).fetchall()
        if event["unit"] == "time_s":
            for row in rows:
                line = competition["name"] + "," + event["name"] + "," + event["unit"]
                line = line + "," + str(row["bib"])
                line = line + "," + row["first_name"] + "," + row["last_name"]
                line = line + "," + row["birth_date"] + "," + row["sex"]
                line = line + "," + (row["club"] or "")
                line = line + "," + row["license_number"]
                line = line + "," + (row["medical_certificate_valid_until"] or "")
                line = line + "," + str(round(row["performance"], 2))
                lines.append(line)
        elif event["unit"] == "distance_m":
            for row in rows:
                line = competition["name"] + "," + event["name"] + "," + event["unit"]
                line = line + "," + str(row["bib"])
                line = line + "," + row["first_name"] + "," + row["last_name"]
                line = line + "," + row["birth_date"] + "," + row["sex"]
                line = line + "," + (row["club"] or "")
                line = line + "," + row["license_number"]
                line = line + "," + (row["medical_certificate_valid_until"] or "")
                line = line + "," + str(round(row["performance"], 2))
                lines.append(line)
        else:
            for row in rows:
                line = competition["name"] + "," + event["name"] + "," + event["unit"]
                line = line + "," + str(row["bib"])
                line = line + "," + row["first_name"] + "," + row["last_name"]
                line = line + "," + row["birth_date"] + "," + row["sex"]
                line = line + "," + (row["club"] or "")
                line = line + "," + row["license_number"]
                line = line + "," + (row["medical_certificate_valid_until"] or "")
                line = line + "," + str(int(row["performance"]))
                lines.append(line)
    return "\n".join(lines) + "\n"
