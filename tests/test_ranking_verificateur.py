import pytest


@pytest.fixture
def ranked_event(client, make_competition, make_event, make_athlete, make_registration):
    """Fabrique : épreuve close, un athlète confirmé par performance (None = sans résultat)."""

    def _make(unit: str, performances: list[float | None]) -> dict:
        competition = make_competition(status="open")
        event = make_event(competition["id"], unit=unit)
        registrations = [
            make_registration(event["id"], make_athlete(f"Athlete{i}")["id"])
            for i in range(len(performances))
        ]
        client.patch(f"/competitions/{competition['id']}", json={"status": "closed"})
        for registration, performance in zip(registrations, performances, strict=True):
            if performance is None:
                continue
            response = client.put(
                f"/registrations/{registration['id']}/result", json={"performance": performance}
            )
            assert response.status_code == 200
        return event

    return _make


def _ranks(client, event) -> list[int]:
    response = client.get(f"/events/{event['id']}/ranking")
    assert response.status_code == 200
    return [e["rank"] for e in response.json()]


def test_ex_aequo_en_tete_puis_rang_saute(client, ranked_event):
    event = ranked_event("time_s", [11.9, 11.9, 12.1])

    assert _ranks(client, event) == [1, 1, 3]


def test_ex_aequo_en_queue(client, ranked_event):
    event = ranked_event("time_s", [11.9, 12.1, 12.1])

    assert _ranks(client, event) == [1, 2, 2]


def test_trois_ex_aequo_saute_de_trois_places(client, ranked_event):
    event = ranked_event("time_s", [12.0, 11.0, 12.0, 12.0, 13.0])

    assert _ranks(client, event) == [1, 2, 2, 2, 5]


def test_deux_groupes_ex_aequo_distincts(client, ranked_event):
    event = ranked_event("time_s", [11.0, 11.0, 12.0, 12.0, 13.0])

    assert _ranks(client, event) == [1, 1, 3, 3, 5]


def test_tous_ex_aequo_ont_le_rang_un(client, ranked_event):
    event = ranked_event("time_s", [12.0, 12.0, 12.0])

    assert _ranks(client, event) == [1, 1, 1]


def test_un_seul_resultat_a_le_rang_un(client, ranked_event):
    event = ranked_event("time_s", [12.0])

    assert _ranks(client, event) == [1]


def test_classement_vide_sans_resultat(client, ranked_event):
    event = ranked_event("time_s", [None, None])

    assert _ranks(client, event) == []


def test_ex_aequo_distance_ordre_decroissant(client, ranked_event):
    event = ranked_event("distance_m", [6.5, 7.0, 7.0, 5.0])

    assert _ranks(client, event) == [1, 1, 3, 4]


def test_ex_aequo_points(client, ranked_event):
    event = ranked_event("points", [800, 800, 750])

    assert _ranks(client, event) == [1, 1, 3]


def test_inscription_sans_resultat_ne_compte_pas_dans_les_rangs(client, ranked_event):
    event = ranked_event("time_s", [None, 12.0, 12.0, 13.0])

    assert _ranks(client, event) == [1, 1, 3]


def test_ex_aequo_apres_correction_d_un_resultat(client, ranked_event):
    event = ranked_event("time_s", [11.0, 12.0, 13.0])
    assert _ranks(client, event) == [1, 2, 3]

    # les inscriptions sont créées dans l'ordre : la 3e a l'id 3 (base neuve)
    response = client.put("/registrations/3/result", json={"performance": 12.0})
    assert response.status_code == 200

    assert _ranks(client, event) == [1, 2, 2]


def test_performances_quasi_egales_ne_sont_pas_ex_aequo(client, ranked_event):
    event = ranked_event("time_s", [12.0, 12.01])

    assert _ranks(client, event) == [1, 2]
