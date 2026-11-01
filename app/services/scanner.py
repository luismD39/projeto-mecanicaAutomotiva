"""Varredura OBD-II simulada: lê a ECU simulada, classifica as leituras e salva o diagnóstico.

O diagnóstico guarda uma cópia (snapshot) de tudo o que foi lido. Assim, o histórico não
muda quando o simulador, os limites ou o catálogo forem alterados depois.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone

from app.services import fault_codes, sensor_status, vehicles
from app.services.errors import ConflictError, NotFoundError
from app.services.simulator import EcuSimulator

logger = logging.getLogger(__name__)

STATUS_LABELS = {"ok": "Sem anormalidades", "warn": "Atenção", "crit": "Crítico"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _plural(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def _summarize(dtc_count: int, alerts: list[dict]) -> tuple[str, str]:
    """Status geral e frase de resumo, a partir dos DTCs e das condições observadas."""
    if any(a["status"] == "crit" for a in alerts):
        status = "crit"
    elif dtc_count or alerts:
        status = "warn"
    else:
        status = "ok"
    if not dtc_count and not alerts:
        return status, "Nenhum código de falha armazenado e nenhuma condição fora dos limites didáticos."
    parts = []
    if dtc_count:
        parts.append(_plural(dtc_count, "código de falha armazenado", "códigos de falha armazenados"))
    if alerts:
        parts.append(_plural(len(alerts), "condição fora do limite didático", "condições fora dos limites didáticos"))
    return status, " e ".join(parts).capitalize() + "."


def start_scan(db: sqlite3.Connection, ecu: EcuSimulator) -> dict:
    vehicle = vehicles.get_active_vehicle(db)
    if vehicle is None:
        raise ConflictError(
            "Nenhum veículo ativo. Cadastre ou selecione um veículo em Veículos antes de iniciar a varredura.",
            code="NO_ACTIVE_VEHICLE",
        )

    started_at = _now()
    snapshot = sensor_status.annotate(ecu.snapshot())
    scenarios = {"mode": snapshot["mode"], "active_scenarios": snapshot["active_scenarios"]}

    found = []
    for code in snapshot["dtcs"]:
        row = db.execute("SELECT id FROM fault_codes WHERE code = ?", (code,)).fetchone()
        if row is None:  # não deve acontecer: um teste garante que os cenários só usam códigos do catálogo
            logger.warning("DTC %s fora do catálogo; ignorado na varredura", code)
            continue
        found.append(row["id"])

    status, summary = _summarize(len(found), snapshot["alerts"])
    with db:
        cur = db.execute(
            "INSERT INTO diagnostics (vehicle_id, started_at, completed_at, source, status, summary,"
            " scenario_snapshot_json, sensor_snapshot_json, findings_json)"
            " VALUES (?, ?, ?, 'simulation', ?, ?, ?, ?, ?)",
            (vehicle["id"], started_at, _now(), status, summary,
             json.dumps(scenarios, ensure_ascii=False), json.dumps(snapshot, ensure_ascii=False), "[]"),
        )
        diagnostic_id = cur.lastrowid
        db.executemany(
            "INSERT INTO diagnostic_faults (diagnostic_id, fault_code_id, status, evidence) VALUES (?, ?, 'stored', ?)",
            [(diagnostic_id, fid, "Código armazenado informado pela ECU simulada durante a varredura.")
             for fid in found],
        )
        db.executemany(
            "INSERT INTO sensor_readings (diagnostic_id, sensor_key, display_name, value, unit, recorded_at, validity)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(diagnostic_id, key, r["label"], r["value"], r["unit"], snapshot["timestamp"], r["validity"])
             for key, r in snapshot["sensors"].items()],
        )
    return get_diagnostic(db, diagnostic_id)


def get_diagnostic(db: sqlite3.Connection, diagnostic_id: int) -> dict:
    row = db.execute(
        "SELECT d.*, v.make, v.model, v.year, v.engine, v.fuel_type, v.mileage_km"
        " FROM diagnostics d JOIN vehicles v ON v.id = d.vehicle_id WHERE d.id = ?",
        (diagnostic_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError("Diagnóstico não encontrado.")

    snapshot = json.loads(row["sensor_snapshot_json"])
    scenarios = json.loads(row["scenario_snapshot_json"])
    faults = [
        {"code": f["code"], "description": f["description"], "system": f["system"],
         "status": f["status"], "evidence": f["evidence"]}
        for f in db.execute(
            "SELECT c.code, c.description, c.system, f.status, f.evidence FROM diagnostic_faults f"
            " JOIN fault_codes c ON c.id = f.fault_code_id WHERE f.diagnostic_id = ? ORDER BY c.code",
            (diagnostic_id,),
        )
    ]
    readings = [
        {**dict(r), "status": snapshot["sensors"].get(r["sensor_key"], {}).get("status"),
         "status_label": snapshot["sensors"].get(r["sensor_key"], {}).get("status_label")}
        for r in db.execute(
            "SELECT sensor_key, display_name, value, unit, validity, recorded_at FROM sensor_readings"
            " WHERE diagnostic_id = ? ORDER BY id",
            (diagnostic_id,),
        )
    ]
    return {
        "diagnostic_id": row["id"],
        "source": row["source"],
        "status": row["status"],
        "status_label": STATUS_LABELS.get(row["status"], row["status"]),
        "summary": row["summary"],
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
        "vehicle": {"id": row["vehicle_id"], "make": row["make"], "model": row["model"], "year": row["year"],
                    "engine": row["engine"], "fuel_label": vehicles.FUEL_TYPES.get(row["fuel_type"], row["fuel_type"]),
                    "mileage_km": row["mileage_km"]},
        "faults": faults,
        "conditions": snapshot.get("alerts", []),
        "readings": readings,
        "fan": snapshot.get("fan"),
        "mode": scenarios.get("mode"),
        "active_scenarios": scenarios.get("active_scenarios", []),
        "findings": json.loads(row["findings_json"]),
        "thresholds_notice": snapshot.get("thresholds_notice", sensor_status.NOTICE),
        "notice": "Simulação didática: não representa leitura de um veículo real.",
        "dtc_note": fault_codes.NOTE,
    }
