from datetime import date, datetime, timedelta, timezone
from io import BytesIO

import pytest
from pypdf import PdfReader

from app.db import connect


def add_vehicle(client, model):
    return client.post("/api/vehicles", json={"make": "Demo", "model": model, "year": 2020, "fuel_type": "flex",
                                              "mileage_km": 1234}).get_json()["id"]


def scan(client):
    return client.post("/api/scanner/start").get_json()


def listed(client, **params):
    resp = client.get("/api/diagnostics", query_string=params)
    assert resp.status_code == 200, resp.get_json()
    return [d["diagnostic_id"] for d in resp.get_json()["diagnostics"]]


def pdf_text(resp) -> str:
    reader = PdfReader(BytesIO(resp.data))
    return "\n".join(page.extract_text() for page in reader.pages)


@pytest.fixture
def two_vehicles(client):
    """Hatch com 2 diagnósticos, Sedan com 1."""
    hatch = add_vehicle(client, "Hatch")
    sedan = add_vehicle(client, "Sedan")
    first = scan(client)["diagnostic_id"]
    second = scan(client)["diagnostic_id"]
    client.post(f"/api/vehicles/{sedan}/activate")
    third = scan(client)["diagnostic_id"]
    return {"hatch": hatch, "sedan": sedan, "ids": [first, second, third]}


# ---------- Histórico (API) ----------

def test_empty_history(client):
    assert listed(client) == []


def test_history_lists_newest_first_with_details(client, two_vehicles):
    data = client.get("/api/diagnostics").get_json()["diagnostics"]
    assert [d["diagnostic_id"] for d in data] == two_vehicles["ids"][::-1]
    newest = data[0]
    assert newest["vehicle"]["model"] == "Sedan"
    assert newest["dtc_count"] == 0
    assert newest["status_label"] == "Sem anormalidades"
    assert newest["summary"]


def test_filter_by_vehicle(client, two_vehicles):
    assert listed(client, vehicle_id=two_vehicles["hatch"]) == two_vehicles["ids"][1::-1]
    assert listed(client, vehicle_id=two_vehicles["sedan"]) == [two_vehicles["ids"][2]]


def test_filter_by_unknown_vehicle_returns_404(client):
    assert client.get("/api/diagnostics?vehicle_id=999").status_code == 404


@pytest.mark.parametrize("params, field", [
    ({"vehicle_id": "abc"}, "vehicle_id"),
    ({"from": "31/10/2026"}, "from"),
    ({"to": "2026-13-01"}, "to"),
    ({"from": "2026-11-02", "to": "2026-11-01"}, "to"),
])
def test_invalid_filters_are_rejected(client, params, field):
    resp = client.get("/api/diagnostics", query_string=params)
    assert resp.status_code == 422
    assert field in resp.get_json()["error"]["fields"]


def test_filter_by_date_range(client, two_vehicles):
    today = date.today()
    all_ids = sorted(two_vehicles["ids"])
    assert sorted(listed(client, **{"from": today.isoformat(), "to": today.isoformat()})) == all_ids
    assert listed(client, **{"from": (today + timedelta(days=1)).isoformat()}) == []
    assert listed(client, to=(today - timedelta(days=1)).isoformat()) == []


def test_date_filter_uses_local_day(client, db_path):
    """Diagnóstico às 23:30 do horário local deve aparecer naquele dia, mesmo sendo outro dia em UTC."""
    add_vehicle(client, "Hatch")
    did = scan(client)["diagnostic_id"]
    late_local = datetime.combine(date(2026, 5, 10), datetime.min.time()).replace(hour=23, minute=30).astimezone()
    conn = connect(db_path)
    # gravado em UTC, como a varredura faz (no Brasil, 23:30 local já é o dia seguinte em UTC)
    conn.execute("UPDATE diagnostics SET completed_at = ? WHERE id = ?",
                 (late_local.astimezone(timezone.utc).isoformat(timespec="seconds"), did))
    conn.commit()
    conn.close()
    assert listed(client, **{"from": "2026-05-10", "to": "2026-05-10"}) == [did]
    assert listed(client, **{"from": "2026-05-11"}) == []


def test_history_page_offers_vehicle_filter(client, two_vehicles):
    html = client.get("/historico").get_data(as_text=True)
    assert f'<option value="{two_vehicles["hatch"]}">Demo Hatch 2020</option>' in html
    assert 'type="date"' in html and "js/history.js" in html


# ---------- Relatório PDF ----------

def test_pdf_for_existing_diagnostic(client):
    add_vehicle(client, "Hatch")
    client.post("/api/simulator/scenarios/misfire_cyl1/activate")
    d = scan(client)
    resp = client.get(f"/api/reports/{d['diagnostic_id']}/pdf")
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data.startswith(b"%PDF")
    assert f'filename="autoscan-diagnostico-{d["diagnostic_id"]}.pdf"' in resp.headers["Content-Disposition"]
    assert resp.headers["Content-Disposition"].startswith("attachment")


def test_pdf_contains_required_information(client):
    add_vehicle(client, "Hatch")
    client.post("/api/simulator/scenarios/misfire_cyl1/activate")
    d = scan(client)
    text = pdf_text(client.get(f"/api/reports/{d['diagnostic_id']}/pdf"))
    when = datetime.fromisoformat(d["completed_at"]).astimezone().strftime("%d/%m/%Y")

    assert "AutoScan Pro" in text
    assert "SIMULAÇÃO DIDÁTICA: não representa leitura de um veículo real" in text
    assert "Demo Hatch 2020" in text  # veículo
    assert when in text  # data
    assert str(d["diagnostic_id"]) in text  # identificador
    assert "P0301" in text and "Falha de combustão detectada no cilindro 1" in text  # códigos
    assert "Falha de combustão registrada" in text  # análise por regras
    assert "não confirma" in text  # ressalva do DTC
    assert "Rotação do motor" in text and "Tensão do módulo" in text  # leituras
    assert "Página 1" in text


def test_pdf_without_faults(client):
    add_vehicle(client, "Hatch")
    d = scan(client)
    text = pdf_text(client.get(f"/api/reports/{d['diagnostic_id']}/pdf"))
    assert "Nenhum código de falha armazenado" in text
    assert "Nenhuma regra disparada" in text


def test_pdf_with_invalid_sensor_reading(client):
    add_vehicle(client, "Hatch")
    client.post("/api/simulator/scenarios/ect_disconnected/activate")
    d = scan(client)
    text = pdf_text(client.get(f"/api/reports/{d['diagnostic_id']}/pdf"))
    assert "Sem leitura" in text and "P0115" in text


def test_pdf_is_the_same_after_simulator_changes(client):
    add_vehicle(client, "Hatch")
    client.post("/api/simulator/scenarios/lean_mixture/activate")
    d = scan(client)
    before = pdf_text(client.get(f"/api/reports/{d['diagnostic_id']}/pdf"))
    client.post("/api/simulator/reset")
    client.post("/api/simulator/scenarios/low_voltage/activate")
    after = pdf_text(client.get(f"/api/reports/{d['diagnostic_id']}/pdf"))
    assert before == after


def test_pdf_for_missing_diagnostic_returns_404(client):
    resp = client.get("/api/reports/999/pdf")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["message"] == "Diagnóstico não encontrado."
