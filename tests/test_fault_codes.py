import json

import pytest

from app import create_app
from app.db import connect
from app.services.fault_codes import load_catalog
from app.services.simulator import SCENARIOS

SPEC_CODES = {"P0101", "P0115", "P0128", "P0171", "P0300", "P0301", "P0420", "P0500"}


def codes(client, q=""):
    return [c["code"] for c in client.get("/api/fault-codes", query_string={"q": q}).get_json()["fault_codes"]]


def test_catalog_has_the_specified_codes_with_complete_content():
    entries = load_catalog()
    assert {e["code"] for e in entries} == SPEC_CODES
    for e in entries:
        assert len(e["causes"]) >= 3 and len(e["symptoms"]) >= 3 and len(e["checks"]) >= 3, e["code"]


def test_invalid_catalog_entry_is_rejected(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps([{"code": "P0000", "description": "x", "system": "y", "explanation": "z",
                                "causes": [], "symptoms": ["a"], "checks": ["b"]}]), encoding="utf-8")
    with pytest.raises(ValueError, match="causes"):
        load_catalog(bad)


def test_every_simulated_dtc_exists_in_catalog():
    catalog = {e["code"] for e in load_catalog()}
    for info in SCENARIOS.values():
        assert set(info["dtcs"]) <= catalog


def test_seed_runs_repeatedly_without_duplicates(db_path):
    for _ in range(3):
        create_app({"TESTING": True, "DATABASE": db_path})
    conn = connect(db_path)
    assert conn.execute("SELECT COUNT(*) FROM fault_codes").fetchone()[0] == len(SPEC_CODES)
    conn.close()


def test_list_all_codes_sorted(client):
    assert codes(client) == sorted(SPEC_CODES)


def test_search_by_exact_code_and_prefix(client):
    assert codes(client, "P0301") == ["P0301"]
    assert codes(client, "p030") == ["P0300", "P0301"]


@pytest.mark.parametrize("query", ["combustão", "COMBUSTAO", "falha combustao"])
def test_search_by_text_ignores_accents_and_case(client, query):
    assert {"P0300", "P0301"} <= set(codes(client, query))


def test_search_by_description_words(client):
    assert codes(client, "muito pobre") == ["P0171"]
    assert {"P0171", "P0300"} <= set(codes(client, "pobre"))  # P0300 cita mistura pobre como causa
    assert "P0500" in codes(client, "velocidade")
    assert codes(client, "xyzinexistente") == []


def test_search_rejects_too_long_query(client):
    resp = client.get("/api/fault-codes", query_string={"q": "x" * 51})
    assert resp.status_code == 422


def test_detail(client):
    data = client.get("/api/fault-codes/p0301").get_json()  # minúsculas também funcionam
    assert data["code"] == "P0301"
    assert "cilindro 1" in data["description"]
    assert data["causes"] and data["symptoms"] and data["checks"]
    assert "não confirma sozinho qual peça está defeituosa" in data["note"]
    assert "variam conforme veículo, motor e fabricante" in data["note"]


def test_detail_missing_code_returns_404(client):
    resp = client.get("/api/fault-codes/P9999")
    assert resp.status_code == 404
    assert resp.get_json()["error"]["message"] == "Código não encontrado no catálogo."


def test_codes_page(client):
    html = client.get("/codigos-dtc").get_data(as_text=True)
    assert 'id="q"' in html and "js/codes.js" in html
