def test_live_snapshot(client):
    resp = client.get("/api/sensors/live")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["source"] == "simulation"
    assert "não representam leitura de um veículo real" in data["notice"]
    assert data["sensors"]["rpm"]["unit"] == "rpm"
    assert data["sensors"]["coolant_temperature"]["unit"] == "°C"
    assert data["fan"] == {"on": False}
    assert data["timestamp"].endswith("+00:00")


def test_set_mode(client):
    resp = client.post("/api/simulator/mode", json={"mode": "accelerating"})
    assert resp.status_code == 200
    assert resp.get_json()["mode"] == "accelerating"
    assert client.get("/api/sensors/live").get_json()["mode"] == "accelerating"


def test_set_mode_rejects_invalid(client):
    resp = client.post("/api/simulator/mode", json={"mode": "turbo"})
    assert resp.status_code == 422
    assert "mode" in resp.get_json()["error"]["fields"]
    assert client.post("/api/simulator/mode", data="idle").status_code == 422


def test_list_scenarios(client):
    data = client.get("/api/simulator/scenarios").get_json()
    ids = {s["id"] for s in data["scenarios"]}
    assert ids == {"overheating", "low_voltage", "ect_disconnected", "misfire_cyl1", "lean_mixture", "vss_failure"}
    assert not any(s["active"] for s in data["scenarios"])
    overheating = next(s for s in data["scenarios"] if s["id"] == "overheating")
    assert overheating["conflicts_with"] == ["ect_disconnected"]


def test_activate_and_deactivate_scenario(client):
    resp = client.post("/api/simulator/scenarios/misfire_cyl1/activate")
    assert resp.status_code == 200
    assert client.get("/api/sensors/live").get_json()["dtcs"] == ["P0301"]

    client.post("/api/simulator/scenarios/misfire_cyl1/deactivate")
    assert client.get("/api/sensors/live").get_json()["dtcs"] == []


def test_unknown_scenario_returns_404(client):
    resp = client.post("/api/simulator/scenarios/explosao/activate")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["message"] == "Cenário não encontrado."


def test_conflicting_scenario_returns_409(client):
    client.post("/api/simulator/scenarios/overheating/activate")
    resp = client.post("/api/simulator/scenarios/ect_disconnected/activate")
    assert resp.status_code == 409
    error = resp.get_json()["error"]
    assert error["code"] == "SCENARIO_CONFLICT"
    assert "Superaquecimento" in error["message"]


def test_reset(client):
    client.post("/api/simulator/mode", json={"mode": "accelerating"})
    client.post("/api/simulator/scenarios/lean_mixture/activate")
    data = client.post("/api/simulator/reset").get_json()
    assert data["mode"] == "idle"
    assert not any(s["active"] for s in data["scenarios"])
    assert client.get("/api/sensors/live").get_json()["dtcs"] == []


def test_each_app_has_its_own_simulator(app, db_path):
    from app import create_app

    app.test_client().post("/api/simulator/scenarios/low_voltage/activate")
    other = create_app({"TESTING": True, "DATABASE": db_path}).test_client()
    assert other.get("/api/sensors/live").get_json()["active_scenarios"] == []
