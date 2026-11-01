import re

from app.services.simulator import SCENARIOS


def lab_html(client):
    resp = client.get("/laboratorio")
    assert resp.status_code == 200
    return resp.get_data(as_text=True)


def card(html, scenario_id):
    return re.search(rf'<article class="card scenario" data-scenario="{scenario_id}".*?</article>', html, re.S).group(0)


def test_lab_lists_every_scenario_with_working_controls(client):
    html = lab_html(client)
    for sid, info in SCENARIOS.items():
        c = card(html, sid)
        assert info["name"] in c and info["description"] in c
        assert f'aria-label="Ativar {info["name"]}"' in c
    assert 'id="reset-btn"' in html and "Restaurar condições normais" in html
    assert "js/lab.js" in html


def test_lab_shows_which_dtc_each_scenario_generates(client):
    html = lab_html(client)
    assert 'href="/codigos-dtc?codigo=P0301"' in card(html, "misfire_cyl1")
    assert "Não gera DTC" in card(html, "overheating")


def test_lab_explains_conflicts(client):
    c = card(lab_html(client), "ect_disconnected")
    assert 'data-conflicts="overheating"' in c
    assert 'Não pode ficar ativo junto com "Superaquecimento"' in c


def test_lab_reflects_current_simulator_state(client):
    html = lab_html(client)
    assert "Nenhum: a ECU simulada está em condições normais." in html

    client.post("/api/simulator/scenarios/low_voltage/activate")
    html = lab_html(client)
    c = card(html, "low_voltage")
    assert 'data-active="true"' in c
    assert 'aria-label="Desativar Tensão baixa"' in c
    active_list = re.search(r'id="active-list"[^>]*>(.*?)</p>', html, re.S).group(1).strip()
    assert active_list == "Tensão baixa"


def test_lab_shows_live_effect_tiles(client):
    html = lab_html(client)
    for key in ("coolant_temperature", "battery_voltage", "rpm", "vehicle_speed", "long_term_fuel_trim"):
        assert f'data-sensor="{key}"' in html
    assert 'id="fan-state"' in html


def test_full_demo_can_be_repeated_without_restart(client):
    """Roteiro do laboratório: ativa, varre, restaura, varre de novo, repete."""
    client.post("/api/vehicles", json={"make": "Demo", "model": "Hatch", "year": 2020, "fuel_type": "flex"})
    for _ in range(2):
        client.post("/api/simulator/scenarios/misfire_cyl1/activate")
        faulty = client.post("/api/scanner/start").get_json()
        assert [f["code"] for f in faulty["faults"]] == ["P0301"]

        client.post("/api/simulator/reset")
        clean = client.post("/api/scanner/start").get_json()
        assert clean["faults"] == [] and clean["status"] == "ok"

        # o diagnóstico com falha continua igual depois do reset
        assert client.get(f"/api/diagnostics/{faulty['diagnostic_id']}").get_json() == faulty
