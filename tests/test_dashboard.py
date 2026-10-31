from app.db import connect


def add_vehicle_with_diagnostic(db_path):
    conn = connect(db_path)
    cur = conn.execute(
        "INSERT INTO vehicles (make, model, year, fuel_type, created_at, updated_at, is_active)"
        " VALUES ('Demo', 'Hatch', 2020, 'flex', 't', 't', 1)"
    )
    diag = conn.execute(
        "INSERT INTO diagnostics (vehicle_id, started_at, completed_at, status, summary,"
        " scenario_snapshot_json, sensor_snapshot_json, findings_json)"
        " VALUES (?, '2026-10-31T21:00:00+00:00', '2026-10-31T21:00:05+00:00', 'warn',"
        " 'Falha de combustão detectada', '{}', '{}', '[]')",
        (cur.lastrowid,),
    )
    conn.execute(
        "INSERT INTO fault_codes (code, description, system, explanation, causes_json, symptoms_json,"
        " checks_json, created_at) VALUES ('P0301', 'd', 's', 'e', '[]', '[]', '[]', 't')"
    )
    conn.execute("INSERT INTO diagnostic_faults (diagnostic_id, fault_code_id) VALUES (?, 1)", (diag.lastrowid,))
    conn.commit()
    conn.close()


def test_live_endpoint_includes_status_and_alerts(client):
    data = client.get("/api/sensors/live").get_json()
    assert data["alerts"] == []
    assert data["sensors"]["rpm"]["status"] == "normal"
    assert data["sensors"]["rpm"]["status_label"] == "Normal"


def test_dashboard_has_tiles_charts_and_local_chartjs(client):
    html = client.get("/").get_data(as_text=True)
    for key in ("rpm", "coolant_temperature", "vehicle_speed", "engine_load", "throttle_position", "battery_voltage"):
        assert f'data-sensor="{key}"' in html
    assert 'id="chart-rpm"' in html and 'id="chart-ect"' in html
    assert "/static/vendor/chart.umd.min.js" in html
    assert "cdn" not in html.lower()  # nada carregado da internet
    assert "Origem: ECU simulada" in html


def test_dashboard_without_diagnostics(client):
    html = client.get("/").get_data(as_text=True)
    assert "Sem diagnóstico" in html  # sem veículo ativo


def test_dashboard_shows_last_diagnostic(client, db_path):
    add_vehicle_with_diagnostic(db_path)
    html = client.get("/").get_data(as_text=True)
    assert "Falha de combustão detectada" in html
    assert "<dd>1</dd>" in html  # 1 DTC
    assert "31/10/2026" in html


def test_live_page_has_all_sensors_and_mode_buttons(client):
    html = client.get("/dados-em-tempo-real").get_data(as_text=True)
    assert html.count('class="kpi"') == 9
    for mode in ("idle", "accelerating", "decelerating"):
        assert f'data-mode="{mode}"' in html
    assert 'id="chart-sensor"' in html
    assert "não é leitura de veículo real" in html


def test_chartjs_file_is_served(client):
    resp = client.get("/static/vendor/chart.umd.min.js")
    assert resp.status_code == 200
    assert b"Chart.js v4" in resp.data[:200]
