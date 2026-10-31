from datetime import datetime

import pytest

from app import create_app
from app.db import connect

VALID = {
    "make": "Volkswagen",
    "model": "Golf",
    "year": 2018,
    "engine": "1.4 TSI",
    "fuel_type": "gasolina",
    "mileage_km": 78500,
}


def create(client, **changes):
    return client.post("/api/vehicles", json={**VALID, **changes})


def add_diagnostic(db_path, vehicle_id):
    conn = connect(db_path)
    conn.execute(
        "INSERT INTO diagnostics (vehicle_id, started_at, completed_at, status, summary,"
        " scenario_snapshot_json, sensor_snapshot_json, findings_json)"
        " VALUES (?, 't', 't', 'ok', 'teste', '{}', '{}', '[]')",
        (vehicle_id,),
    )
    conn.commit()
    conn.close()


def test_create_valid_vehicle(client):
    resp = create(client)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["make"] == "Volkswagen"
    assert data["fuel_label"] == "Gasolina"
    assert data["mileage_km"] == 78500
    assert data["created_at"] and data["updated_at"]


def test_first_vehicle_becomes_active_others_do_not(client):
    assert create(client).get_json()["is_active"] is True
    assert create(client, model="Polo").get_json()["is_active"] is False


def test_text_is_trimmed_and_engine_optional(client):
    data = create(client, make="  Fiat ", model=" Uno ", engine="  ").get_json()
    assert (data["make"], data["model"], data["engine"]) == ("Fiat", "Uno", None)


def test_mileage_defaults_to_zero(client):
    payload = {k: v for k, v in VALID.items() if k != "mileage_km"}
    assert client.post("/api/vehicles", json=payload).get_json()["mileage_km"] == 0


@pytest.mark.parametrize("field", ["make", "model"])
@pytest.mark.parametrize("value", ["", "   ", None, 123])
def test_rejects_empty_make_or_model(client, field, value):
    resp = create(client, **{field: value})
    assert resp.status_code == 422
    error = resp.get_json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert field in error["fields"]


@pytest.mark.parametrize("year", [1995, datetime.now().year + 2, "abc", 2018.5, True, None])
def test_rejects_year_out_of_range(client, year):
    resp = create(client, year=year)
    assert resp.status_code == 422
    assert "year" in resp.get_json()["error"]["fields"]


def test_accepts_year_limits(client):
    assert create(client, year=1996).status_code == 201
    assert create(client, year=datetime.now().year + 1).status_code == 201


@pytest.mark.parametrize("mileage", [-1, 2_000_001, "muito", float("inf")])
def test_rejects_invalid_mileage(client, mileage):
    resp = create(client, mileage_km=mileage)
    assert resp.status_code == 422
    assert "mileage_km" in resp.get_json()["error"]["fields"]


def test_rejects_unknown_fuel_type(client):
    resp = create(client, fuel_type="querosene")
    assert resp.status_code == 422
    assert "fuel_type" in resp.get_json()["error"]["fields"]


def test_rejects_too_long_text(client):
    resp = create(client, make="x" * 61)
    assert "make" in resp.get_json()["error"]["fields"]


def test_rejects_body_that_is_not_json(client):
    resp = client.post("/api/vehicles", data="make=Fiat")
    assert resp.status_code == 422
    assert resp.get_json()["error"]["message"] == "Envie os dados do veículo em formato JSON."


def test_reports_all_invalid_fields_at_once(client):
    resp = client.post("/api/vehicles", json={})
    assert set(resp.get_json()["error"]["fields"]) == {"make", "model", "year", "fuel_type"}


def test_list_and_get(client):
    vid = create(client).get_json()["id"]
    create(client, model="Polo")
    listed = client.get("/api/vehicles").get_json()["vehicles"]
    assert len(listed) == 2
    assert listed[0]["id"] == vid  # o ativo vem primeiro
    assert client.get(f"/api/vehicles/{vid}").get_json()["model"] == "Golf"


def test_get_missing_vehicle_returns_404(client):
    resp = client.get("/api/vehicles/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["message"] == "Veículo não encontrado."


def test_update_vehicle(client):
    vid = create(client).get_json()["id"]
    resp = client.put(f"/api/vehicles/{vid}", json={**VALID, "mileage_km": 80000, "engine": None})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["mileage_km"] == 80000
    assert data["engine"] is None
    assert data["is_active"] is True  # editar não muda o ativo


def test_update_validates_and_404(client):
    vid = create(client).get_json()["id"]
    assert client.put(f"/api/vehicles/{vid}", json={**VALID, "year": 1900}).status_code == 422
    assert client.get(f"/api/vehicles/{vid}").get_json()["year"] == 2018
    assert client.put("/api/vehicles/999", json=VALID).status_code == 404


def test_only_one_active_vehicle(client):
    first = create(client).get_json()["id"]
    second = create(client, model="Polo").get_json()["id"]
    resp = client.post(f"/api/vehicles/{second}/activate")
    assert resp.status_code == 200
    assert resp.get_json()["is_active"] is True
    active = [v["id"] for v in client.get("/api/vehicles").get_json()["vehicles"] if v["is_active"]]
    assert active == [second]
    assert client.get(f"/api/vehicles/{first}").get_json()["is_active"] is False


def test_activate_missing_vehicle_returns_404(client):
    assert client.post("/api/vehicles/999/activate").status_code == 404


def test_delete_vehicle_without_history(client):
    vid = create(client).get_json()["id"]
    assert client.delete(f"/api/vehicles/{vid}").status_code == 204
    assert client.get(f"/api/vehicles/{vid}").status_code == 404
    assert client.delete(f"/api/vehicles/{vid}").status_code == 404


def test_delete_blocked_when_vehicle_has_history(client, db_path):
    vid = create(client).get_json()["id"]
    add_diagnostic(db_path, vid)
    resp = client.delete(f"/api/vehicles/{vid}")
    assert resp.status_code == 409
    error = resp.get_json()["error"]
    assert error["code"] == "VEHICLE_HAS_HISTORY"
    assert "1 diagnóstico" in error["message"]
    assert client.get(f"/api/vehicles/{vid}").get_json()["diagnostic_count"] == 1


def test_vehicle_persists_after_restart(db_path):
    first_run = create_app({"TESTING": True, "DATABASE": db_path}).test_client()
    vid = create(first_run).get_json()["id"]

    second_run = create_app({"TESTING": True, "DATABASE": db_path}).test_client()
    data = second_run.get(f"/api/vehicles/{vid}").get_json()
    assert data["model"] == "Golf"
    assert data["is_active"] is True


def test_vehicles_page_has_form_and_fuel_options(client):
    html = client.get("/veiculos").get_data(as_text=True)
    assert 'id="vehicle-form"' in html
    assert '<option value="hibrido">Híbrido</option>' in html
    assert 'min="1996"' in html
    assert "dados fictícios" in html
