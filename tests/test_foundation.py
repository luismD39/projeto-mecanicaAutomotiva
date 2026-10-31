import sqlite3

import pytest

from app import create_app
from app.db import connect, init_db

TABLES = {"vehicles", "fault_codes", "diagnostics", "diagnostic_faults", "sensor_readings"}


def test_health_responds_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
    assert data["source"] == "simulation"


def test_database_has_all_tables(app, db_path):
    conn = connect(db_path)
    names = {r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    conn.close()
    assert TABLES <= names


def test_init_db_is_idempotent(db_path):
    init_db(db_path)
    init_db(db_path)
    create_app({"TESTING": True, "DATABASE": db_path})


def test_foreign_keys_enabled(app, db_path):
    conn = connect(db_path)
    assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO diagnostics (vehicle_id, started_at, completed_at, status, summary,"
            " scenario_snapshot_json, sensor_snapshot_json, findings_json)"
            " VALUES (999, 't', 't', 'ok', 's', '{}', '{}', '[]')"
        )
    conn.close()


def test_only_one_active_vehicle(app, db_path):
    conn = connect(db_path)
    sql = (
        "INSERT INTO vehicles (make, model, year, fuel_type, created_at, updated_at, is_active)"
        " VALUES ('Demo', 'Teste', 2020, 'flex', 't', 't', 1)"
    )
    conn.execute(sql)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(sql)
    conn.close()


def test_unknown_api_route_returns_json_error(client):
    resp = client.get("/api/nao-existe")
    assert resp.status_code == 404
    assert resp.get_json() == {"error": {"code": "NOT_FOUND", "message": "Recurso não encontrado."}}


def test_wrong_method_returns_json_error(client):
    resp = client.post("/api/health")
    assert resp.status_code == 405
    assert resp.get_json()["error"]["code"] == "METHOD_NOT_ALLOWED"
