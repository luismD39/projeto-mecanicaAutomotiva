"""Regras de negócio de veículos: validação, cadastro, veículo ativo e política de exclusão."""

import math
import sqlite3
from datetime import datetime, timezone

from app.services.errors import ConflictError, NotFoundError, ValidationError

FUEL_TYPES = {
    "gasolina": "Gasolina",
    "etanol": "Etanol",
    "flex": "Flex",
    "diesel": "Diesel",
    "gnv": "GNV",
    "hibrido": "Híbrido",
    "eletrico": "Elétrico",
    "outro": "Outro",
}

# O OBD-II passou a ser obrigatório nos EUA em 1996; usado aqui como limite didático inferior.
YEAR_MIN = 1996
MILEAGE_MAX_KM = 2_000_000
TEXT_LIMITS = {"make": 60, "model": 60, "engine": 40}

_SELECT = """
    SELECT v.id, v.make, v.model, v.year, v.engine, v.fuel_type, v.mileage_km, v.is_active,
           v.created_at, v.updated_at,
           (SELECT COUNT(*) FROM diagnostics d WHERE d.vehicle_id = v.id) AS diagnostic_count
    FROM vehicles v
"""


def year_max() -> int:
    return datetime.now().year + 1  # o ano-modelo pode ser o ano seguinte


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _to_dict(row: sqlite3.Row) -> dict:
    vehicle = dict(row)
    vehicle["is_active"] = bool(vehicle["is_active"])
    vehicle["fuel_label"] = FUEL_TYPES.get(vehicle["fuel_type"], vehicle["fuel_type"])
    return vehicle


def _parse_int(value) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _parse_number(value) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def validate(data) -> dict:
    """Valida e normaliza os dados do formulário. Lança ValidationError com uma mensagem por campo."""
    if not isinstance(data, dict):
        raise ValidationError("Envie os dados do veículo em formato JSON.")

    errors: dict[str, str] = {}
    clean: dict = {}

    for field, message in (("make", "Informe o fabricante/marca."), ("model", "Informe o modelo.")):
        value = data.get(field)
        value = value.strip() if isinstance(value, str) else ""
        if not value:
            errors[field] = message
        elif len(value) > TEXT_LIMITS[field]:
            errors[field] = f"Use no máximo {TEXT_LIMITS[field]} caracteres."
        clean[field] = value

    engine = data.get("engine")
    if engine is None or (isinstance(engine, str) and not engine.strip()):
        clean["engine"] = None
    elif not isinstance(engine, str):
        errors["engine"] = "Motorização inválida."
    elif len(engine.strip()) > TEXT_LIMITS["engine"]:
        errors["engine"] = f"Use no máximo {TEXT_LIMITS['engine']} caracteres."
    else:
        clean["engine"] = engine.strip()

    year = _parse_int(data.get("year"))
    if year is None or not YEAR_MIN <= year <= year_max():
        errors["year"] = f"Informe um ano entre {YEAR_MIN} e {year_max()}."
    clean["year"] = year

    fuel_type = data.get("fuel_type")
    if fuel_type not in FUEL_TYPES:
        errors["fuel_type"] = "Escolha um tipo de combustível da lista."
    clean["fuel_type"] = fuel_type

    mileage_raw = data.get("mileage_km")
    mileage = 0.0 if mileage_raw in (None, "") else _parse_number(mileage_raw)
    if mileage is None or not 0 <= mileage <= MILEAGE_MAX_KM:
        errors["mileage_km"] = "Informe uma quilometragem entre 0 e 2.000.000 km."
    clean["mileage_km"] = mileage

    if errors:
        raise ValidationError("Verifique os campos informados.", fields=errors)
    return clean


def list_vehicles(db: sqlite3.Connection) -> list[dict]:
    rows = db.execute(_SELECT + " ORDER BY v.is_active DESC, v.make, v.model, v.id").fetchall()
    return [_to_dict(r) for r in rows]


def get_vehicle(db: sqlite3.Connection, vehicle_id: int) -> dict:
    row = db.execute(_SELECT + " WHERE v.id = ?", (vehicle_id,)).fetchone()
    if row is None:
        raise NotFoundError("Veículo não encontrado.")
    return _to_dict(row)


def get_active_vehicle(db: sqlite3.Connection) -> dict | None:
    row = db.execute(_SELECT + " WHERE v.is_active = 1").fetchone()
    return _to_dict(row) if row else None


def create_vehicle(db: sqlite3.Connection, data) -> dict:
    clean = validate(data)
    now = _now()
    with db:
        # Se ainda não há veículo ativo, o novo já fica ativo (agiliza a demonstração).
        has_active = db.execute("SELECT 1 FROM vehicles WHERE is_active = 1").fetchone() is not None
        cur = db.execute(
            "INSERT INTO vehicles (make, model, year, engine, fuel_type, mileage_km, created_at, updated_at, is_active)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (clean["make"], clean["model"], clean["year"], clean["engine"], clean["fuel_type"],
             clean["mileage_km"], now, now, 0 if has_active else 1),
        )
    return get_vehicle(db, cur.lastrowid)


def update_vehicle(db: sqlite3.Connection, vehicle_id: int, data) -> dict:
    get_vehicle(db, vehicle_id)
    clean = validate(data)
    with db:
        db.execute(
            "UPDATE vehicles SET make = ?, model = ?, year = ?, engine = ?, fuel_type = ?, mileage_km = ?,"
            " updated_at = ? WHERE id = ?",
            (clean["make"], clean["model"], clean["year"], clean["engine"], clean["fuel_type"],
             clean["mileage_km"], _now(), vehicle_id),
        )
    return get_vehicle(db, vehicle_id)


def activate_vehicle(db: sqlite3.Connection, vehicle_id: int) -> dict:
    get_vehicle(db, vehicle_id)
    with db:  # transação: desativa o anterior e ativa o novo juntos
        db.execute("UPDATE vehicles SET is_active = 0 WHERE is_active = 1")
        db.execute("UPDATE vehicles SET is_active = 1 WHERE id = ?", (vehicle_id,))
    return get_vehicle(db, vehicle_id)


def delete_vehicle(db: sqlite3.Connection, vehicle_id: int) -> None:
    """Política: veículo com diagnósticos no histórico não pode ser excluído (o histórico é preservado)."""
    vehicle = get_vehicle(db, vehicle_id)
    count = vehicle["diagnostic_count"]
    if count:
        raise ConflictError(
            f"Este veículo possui {count} diagnóstico(s) no histórico e não pode ser excluído. "
            "O histórico é preservado para consulta.",
            code="VEHICLE_HAS_HISTORY",
        )
    with db:
        db.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
