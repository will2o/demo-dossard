from datetime import date
from pathlib import Path


def test_create_athlete_returns_201_with_category(client):
    birth_date = date(date.today().year - 30, 3, 2)

    response = client.post(
        "/athletes",
        json={
            "first_name": "Inès",
            "last_name": "Morel",
            "birth_date": birth_date.isoformat(),
            "sex": "F",
            "license_number": "DOS-000042",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["category"] == "SENIOR"
    assert body["club"] is None


def test_create_athlete_rejects_duplicate_license(client, make_athlete):
    athlete = make_athlete()

    response = client.post(
        "/athletes",
        json={
            "first_name": "Hugo",
            "last_name": "Lemaire",
            "birth_date": "1995-05-20",
            "sex": "M",
            "license_number": athlete["license_number"],
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_list_athletes_filters_by_club(client, make_athlete):
    make_athlete("Durand", club="AC Rivebelle")
    make_athlete("Petit", club="Stade Nordval")

    response = client.get("/athletes", params={"club": "AC Rivebelle"})

    assert response.status_code == 200
    assert [a["last_name"] for a in response.json()] == ["Durand"]


def test_list_athletes_paginates_with_defaults(client, make_athlete):
    for i in range(55):
        make_athlete(f"Nom{i:03d}")

    response = client.get("/athletes")

    assert response.status_code == 200
    assert len(response.json()) == 50
    assert response.json()[0]["last_name"] == "Nom000"


def test_list_athletes_applies_limit_and_offset(client, make_athlete):
    for i in range(5):
        make_athlete(f"Nom{i}")

    response = client.get("/athletes", params={"limit": 2, "offset": 1})

    assert [a["last_name"] for a in response.json()] == ["Nom1", "Nom2"]


def test_list_athletes_accepts_bounds(client, make_athlete):
    make_athlete("Durand")

    assert client.get("/athletes", params={"limit": 1}).status_code == 200
    assert client.get("/athletes", params={"limit": 100}).status_code == 200
    assert client.get("/athletes", params={"offset": 0}).status_code == 200
    assert client.get("/athletes", params={"offset": 10}).json() == []


def test_list_athletes_rejects_out_of_range_pagination(client):
    for params in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "abc"}):
        assert client.get("/athletes", params=params).status_code == 422


def test_list_athletes_paginates_after_club_filter(client, make_athlete):
    make_athlete("Aubert", club="Stade Nordval")
    for name in ("Bernard", "Colin", "Durand"):
        make_athlete(name, club="AC Rivebelle")

    response = client.get("/athletes", params={"club": "AC Rivebelle", "limit": 2, "offset": 1})

    assert [a["last_name"] for a in response.json()] == ["Colin", "Durand"]


def test_get_athlete_returns_athlete_with_category(client, make_athlete):
    athlete = make_athlete("Durand", club="AC Rivebelle")

    response = client.get(f"/athletes/{athlete['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == athlete["id"]
    assert body["last_name"] == "Durand"
    assert body["club"] == "AC Rivebelle"
    assert body["category"] == "SENIOR"


def test_get_athlete_returns_404_when_unknown(client):
    response = client.get("/athletes/999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Athlète 999 introuvable"},
    }


def test_get_athlete_returns_422_on_invalid_id(client):
    response = client.get("/athletes/abc")

    assert response.status_code == 422


CSV_EXEMPLE = Path(__file__).parent.parent / "scripts" / "legacy" / "licencies_exemple.csv"
ERREURS_EXEMPLE = [
    {"line": 15, "message": "date de naissance invalide : « 31/02/2001 » (attendu jj/mm/aaaa)"},
    {"line": 16, "message": "license_number : String should match pattern '^DOS-\\d{6}$'"},
]


def _import_csv(client, content: bytes):
    return client.post("/athletes/import", content=content, headers={"Content-Type": "text/csv"})


def test_import_athletes_creates_skips_and_reports_errors(client):
    response = _import_csv(client, CSV_EXEMPLE.read_bytes())

    assert response.status_code == 200
    body = response.json()
    assert (body["created"], body["skipped"]) == (17, 1)
    assert [e["line"] for e in body["errors"]] == [15, 16]
    assert len(client.get("/athletes").json()) == 17


def test_import_athletes_twice_skips_everything(client):
    content = CSV_EXEMPLE.read_bytes()
    first = _import_csv(client, content).json()

    body = _import_csv(client, content).json()

    assert (body["created"], body["skipped"]) == (0, 18)
    assert body["errors"] == first["errors"]
    assert len(body["errors"]) == 2


def test_import_athletes_rejects_missing_columns(client):
    response = _import_csv(client, b"nom;prenom\nValette;Margaux\n")

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_csv"


def test_import_athletes_rejects_wrong_header(client):
    header = "last_name;first_name;birth_date;sex;club;license;certificate"
    row = "Valette;Margaux;14/03/1998;F;;DOS-900101;"
    response = _import_csv(client, f"{header}\n{row}\n".encode())

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "invalid_csv"
    assert "nom" in error["message"]
    assert client.get("/athletes").json() == []
