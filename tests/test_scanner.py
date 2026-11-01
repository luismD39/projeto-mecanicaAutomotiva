import pytest

from app.db import connect

VEHICLE = {"make": "Demo", "model": "Hatch", "year": 2020, "fuel_type": "flex", "mileage_km": 1000}


@pytest.fixture
def vehicle_id(client):
    return client.post("/api/vehicles", json=VEHICLE).get_json()["id"]  # o primeiro já fica ativo


def scan(client):
    return client.post("/api/scanner/start")


def test_scan_requires_active_vehicle(client):
    resp = scan(client)
    assert resp.status_code == 409
    assert resp.get_json()["error"]["code"] == "NO_ACTIVE_VEHICLE"


def test_scan_without_faults_is_persisted(client, vehicle_id):
    resp = scan(client)
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["diagnostic_id"] > 0
    assert data["source"] == "simulation"
    assert data["status"] == "ok"
    assert data["faults"] == [] and data["conditions"] == []
    assert data["summary"].startswith("Nenhum código de falha")
    assert data["vehicle"]["id"] == vehicle_id
    assert len(data["readings"]) == 9
    assert client.get(f"/api/diagnostics/{data['diagnostic_id']}").get_json() == data


def test_activated_scenarios_appear_in_result(client, vehicle_id):
    client.post("/api/simulator/scenarios/misfire_cyl1/activate")
    client.post("/api/simulator/scenarios/lean_mixture/activate")
    data = scan(client).get_json()
    assert [f["code"] for f in data["faults"]] == ["P0171", "P0301"]
    assert data["faults"][1]["description"] == "Falha de combustão detectada no cilindro 1"
    assert data["status"] == "warn"
    assert data["active_scenarios"] == ["lean_mixture", "misfire_cyl1"]
    assert "2 códigos de falha armazenados" in data["summary"]


def test_observed_condition_without_dtc(client, vehicle_id):
    client.post("/api/simulator/scenarios/ect_disconnected/activate")
    data = scan(client).get_json()
    ect = next(r for r in data["readings"] if r["sensor_key"] == "coolant_temperature")
    assert ect["value"] is None and ect["validity"] == "invalid"
    assert [f["code"] for f in data["faults"]] == ["P0115"]
    assert data["conditions"][0]["sensor"] == "coolant_temperature"


def test_dtc_is_not_presented_as_confirmed_part(client, vehicle_id):
    client.post("/api/simulator/scenarios/misfire_cyl1/activate")
    data = scan(client).get_json()
    assert "não confirma sozinho qual peça está defeituosa" in data["dtc_note"]
    assert data["faults"][0]["status"] == "stored"
    assert "SIMULA" in data["notice"].upper()


def test_history_does_not_change_when_simulator_changes(client, vehicle_id):
    client.post("/api/simulator/scenarios/vss_failure/activate")
    original = scan(client).get_json()
    client.post("/api/simulator/reset")
    client.post("/api/simulator/scenarios/low_voltage/activate")
    scan(client)
    assert client.get(f"/api/diagnostics/{original['diagnostic_id']}").get_json() == original


def test_readings_and_faults_are_stored_in_tables(client, vehicle_id, db_path):
    client.post("/api/simulator/scenarios/misfire_cyl1/activate")
    did = scan(client).get_json()["diagnostic_id"]
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM sensor_readings WHERE diagnostic_id = ?", (did,)).fetchone()[0] == 9
    assert conn.execute("SELECT COUNT(*) FROM diagnostic_faults WHERE diagnostic_id = ?", (did,)).fetchone()[0] == 1
    row = conn.execute("SELECT source, scenario_snapshot_json FROM diagnostics WHERE id = ?", (did,)).fetchone()
    assert row["source"] == "simulation"
    assert "misfire_cyl1" in row["scenario_snapshot_json"]
    conn.close()


def test_vehicle_with_scan_cannot_be_deleted(client, vehicle_id):
    scan(client)
    assert client.delete(f"/api/vehicles/{vehicle_id}").status_code == 409


def test_dashboard_shows_scan(client, vehicle_id):
    client.post("/api/simulator/scenarios/misfire_cyl1/activate")
    scan(client)
    html = client.get("/").get_data(as_text=True)
    assert "1 código de falha armazenado." in html


def test_scan_stores_rule_findings(client, vehicle_id, db_path):
    client.post("/api/simulator/scenarios/misfire_cyl1/activate")
    data = scan(client).get_json()
    assert [f["rule_id"] for f in data["findings"]] == ["R-COMBUSTAO"]
    assert data["summary"] == "1 código de falha armazenado. 1 resultado na análise por regras."
    conn = connect(db_path)
    stored = conn.execute("SELECT findings_json FROM diagnostics WHERE id = ?", (data["diagnostic_id"],)).fetchone()[0]
    conn.close()
    assert "R-COMBUSTAO" in stored


def test_critical_finding_makes_diagnostic_critical(client, vehicle_id, monkeypatch):
    from app.services import rules

    critical = {"rule_id": "R-TESTE", "title": "t", "level": "crit", "level_label": "Crítico", "evidence": ["e"],
                "hypotheses": ["h"], "checks": ["c"], "related_dtcs": [], "disclaimer": "d"}
    monkeypatch.setattr(rules, "evaluate", lambda snapshot: [critical])
    data = scan(client).get_json()
    assert data["status"] == "crit"
    assert data["status_label"] == "Crítico"


def test_saved_findings_do_not_change_when_rules_change(client, vehicle_id, monkeypatch):
    from app.services import rules

    client.post("/api/simulator/scenarios/misfire_cyl1/activate")
    original = scan(client).get_json()
    monkeypatch.setattr(rules, "evaluate", lambda snapshot: [])
    assert client.get(f"/api/diagnostics/{original['diagnostic_id']}").get_json()["findings"] == original["findings"]


def test_diagnostics_page_without_diagnostics(client):
    html = client.get("/diagnosticos").get_data(as_text=True)
    assert "Nenhum diagnóstico salvo" in html
    assert "diagnostics.js" not in html


def test_diagnostics_page_opens_latest_or_requested(client, vehicle_id):
    first = scan(client).get_json()["diagnostic_id"]
    second = scan(client).get_json()["diagnostic_id"]
    assert f'data-id="{second}"' in client.get("/diagnosticos").get_data(as_text=True)
    assert f'data-id="{first}"' in client.get(f"/diagnosticos?id={first}").get_data(as_text=True)
    # id inválido não quebra a página: cai no mais recente
    assert f'data-id="{second}"' in client.get("/diagnosticos?id=abc").get_data(as_text=True)


def test_dashboard_links_to_its_diagnostic(client, vehicle_id):
    did = scan(client).get_json()["diagnostic_id"]
    assert f'href="/diagnosticos?id={did}"' in client.get("/").get_data(as_text=True)


def test_missing_diagnostic_returns_404(client):
    resp = client.get("/api/diagnostics/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["message"] == "Diagnóstico não encontrado."


def test_scanner_page(client, vehicle_id):
    html = client.get("/scanner").get_data(as_text=True)
    assert 'id="scan-btn"' in html
    assert "Lendo códigos de falha (DTC)" in html
    assert "não um veículo real" in html


def test_scanner_page_without_vehicle_has_no_scan_button(client):
    html = client.get("/scanner").get_data(as_text=True)
    assert 'id="scan-btn"' not in html
    assert "Nenhum veículo ativo" in html
