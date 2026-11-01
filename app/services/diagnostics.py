"""Consultas de diagnósticos salvos. A varredura que os cria fica em scanner.py."""

import sqlite3
from datetime import date, datetime, time, timedelta, timezone

from app.services import vehicles
from app.services.errors import ValidationError
from app.services.scanner import STATUS_LABELS

LIST_LIMIT = 500


def get_latest_id(db: sqlite3.Connection) -> int | None:
    row = db.execute("SELECT id FROM diagnostics ORDER BY completed_at DESC, id DESC LIMIT 1").fetchone()
    return row["id"] if row else None


def get_latest(db: sqlite3.Connection, vehicle_id: int) -> dict | None:
    row = db.execute(
        """
        SELECT d.id, d.completed_at, d.status, d.summary,
               (SELECT COUNT(*) FROM diagnostic_faults f WHERE f.diagnostic_id = d.id) AS dtc_count
        FROM diagnostics d
        WHERE d.vehicle_id = ?
        ORDER BY d.completed_at DESC, d.id DESC
        LIMIT 1
        """,
        (vehicle_id,),
    ).fetchone()
    return dict(row) if row else None


def _local_day_start_utc(day: date) -> str:
    """Início do dia no horário do computador, convertido para UTC (formato salvo no banco)."""
    return datetime.combine(day, time.min).astimezone().astimezone(timezone.utc).isoformat(timespec="seconds")


def parse_filters(db: sqlite3.Connection, args) -> dict:
    """Valida os filtros da URL: vehicle_id, from e to (datas AAAA-MM-DD, no horário local)."""
    errors = {}
    filters = {"vehicle_id": None, "from": None, "to": None}

    raw_vehicle = (args.get("vehicle_id") or "").strip()
    if raw_vehicle:
        if not raw_vehicle.isdigit():
            errors["vehicle_id"] = "Veículo inválido."
        else:
            filters["vehicle_id"] = vehicles.get_vehicle(db, int(raw_vehicle))["id"]  # 404 se não existir

    for key, label in (("from", "inicial"), ("to", "final")):
        raw = (args.get(key) or "").strip()
        if raw:
            try:
                filters[key] = date.fromisoformat(raw)
            except ValueError:
                errors[key] = f"Data {label} inválida. Use o formato AAAA-MM-DD."

    if filters["from"] and filters["to"] and filters["from"] > filters["to"]:
        errors["to"] = "A data final deve ser igual ou posterior à data inicial."
    if errors:
        raise ValidationError("Verifique os filtros informados.", fields=errors)
    return filters


def list_diagnostics(db: sqlite3.Connection, filters: dict) -> list[dict]:
    where, params = [], []
    if filters["vehicle_id"]:
        where.append("d.vehicle_id = ?")
        params.append(filters["vehicle_id"])
    if filters["from"]:
        where.append("d.completed_at >= ?")
        params.append(_local_day_start_utc(filters["from"]))
    if filters["to"]:
        where.append("d.completed_at < ?")  # até o fim do dia final
        params.append(_local_day_start_utc(filters["to"] + timedelta(days=1)))

    rows = db.execute(
        f"""
        SELECT d.id, d.completed_at, d.status, d.summary, v.id AS vehicle_id, v.make, v.model, v.year,
               (SELECT COUNT(*) FROM diagnostic_faults f WHERE f.diagnostic_id = d.id) AS dtc_count
        FROM diagnostics d JOIN vehicles v ON v.id = d.vehicle_id
        {"WHERE " + " AND ".join(where) if where else ""}
        ORDER BY d.completed_at DESC, d.id DESC
        LIMIT {LIST_LIMIT}
        """,  # só os trechos fixos acima entram no SQL; os valores vão como parâmetros
        params,
    ).fetchall()
    return [
        {"diagnostic_id": r["id"], "completed_at": r["completed_at"], "status": r["status"],
         "status_label": STATUS_LABELS.get(r["status"], r["status"]), "summary": r["summary"],
         "dtc_count": r["dtc_count"],
         "vehicle": {"id": r["vehicle_id"], "make": r["make"], "model": r["model"], "year": r["year"]}}
        for r in rows
    ]
