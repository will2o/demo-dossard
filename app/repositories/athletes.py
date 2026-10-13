from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date, datetime

from pydantic import ValidationError

from app.categories import age_category
from app.errors import ApiError, ConflictError, NotFoundError
from app.schemas import AthleteCreate, AthleteOut, ImportLineError, ImportReport

IMPORT_COLUMNS = (
    "nom",
    "prenom",
    "date_naissance",
    "sexe",
    "club",
    "licence",
    "certificat_valide_jusqu",
)


def _to_athlete(row: sqlite3.Row) -> AthleteOut:
    birth_date = date.fromisoformat(row["birth_date"])
    certificate = row["medical_certificate_valid_until"]
    return AthleteOut(
        id=row["id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        birth_date=birth_date,
        sex=row["sex"],
        club=row["club"],
        license_number=row["license_number"],
        medical_certificate_valid_until=date.fromisoformat(certificate) if certificate else None,
        category=age_category(birth_date),
    )


def list_athletes(conn: sqlite3.Connection, club: str | None = None) -> list[AthleteOut]:
    sql = "SELECT * FROM athletes"
    params: tuple[str, ...] = ()
    if club is not None:
        sql += " WHERE club = ?"
        params = (club,)
    sql += " ORDER BY last_name, first_name, id"
    return [_to_athlete(row) for row in conn.execute(sql, params)]


def get_athlete(conn: sqlite3.Connection, athlete_id: int) -> AthleteOut:
    row = conn.execute("SELECT * FROM athletes WHERE id = ?", (athlete_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Athlète {athlete_id} introuvable")
    return _to_athlete(row)


def create_athlete(conn: sqlite3.Connection, data: AthleteCreate) -> AthleteOut:
    existing = conn.execute(
        "SELECT id FROM athletes WHERE license_number = ?", (data.license_number,)
    ).fetchone()
    if existing is not None:
        raise ConflictError(f"Licence {data.license_number} déjà enregistrée")

    certificate = data.medical_certificate_valid_until
    cursor = conn.execute(
        "INSERT INTO athletes (first_name, last_name, birth_date, sex, club, license_number,"
        " medical_certificate_valid_until) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            data.first_name,
            data.last_name,
            data.birth_date.isoformat(),
            data.sex.value,
            data.club,
            data.license_number,
            certificate.isoformat() if certificate else None,
        ),
    )
    row = conn.execute("SELECT * FROM athletes WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return _to_athlete(row)


def _parse_import_date(value: str, label: str) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        raise ValueError(f"{label} invalide : « {value} » (attendu jj/mm/aaaa)") from None


def _row_to_create(row: dict[str, str | None]) -> AthleteCreate:
    cell = {col: (row.get(col) or "").strip() for col in IMPORT_COLUMNS}
    birth_date = _parse_import_date(cell["date_naissance"], "date de naissance")
    if birth_date is None:
        raise ValueError("date de naissance manquante")
    return AthleteCreate(
        last_name=cell["nom"],
        first_name=cell["prenom"],
        birth_date=birth_date,
        sex=cell["sexe"],
        club=cell["club"] or None,
        license_number=cell["licence"],
        medical_certificate_valid_until=_parse_import_date(
            cell["certificat_valide_jusqu"], "certificat médical"
        ),
    )


def import_athletes(conn: sqlite3.Connection, content: str) -> ImportReport:
    reader = csv.DictReader(io.StringIO(content), delimiter=";")
    missing = [col for col in IMPORT_COLUMNS if col not in (reader.fieldnames or [])]
    if missing:
        raise ApiError(f"Colonnes manquantes : {', '.join(missing)}", code="invalid_csv")

    created = 0
    skipped = 0
    errors: list[ImportLineError] = []
    for row in reader:
        try:
            data = _row_to_create(row)
        except ValidationError as exc:
            message = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])} : {err['msg']}" for err in exc.errors()
            )
            errors.append(ImportLineError(line=reader.line_num, message=message))
            continue
        except ValueError as exc:
            errors.append(ImportLineError(line=reader.line_num, message=str(exc)))
            continue
        try:
            create_athlete(conn, data)
        except ConflictError:
            skipped += 1
        else:
            created += 1
    return ImportReport(created=created, skipped=skipped, errors=errors)
