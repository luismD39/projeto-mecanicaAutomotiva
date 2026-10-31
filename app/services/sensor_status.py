"""Classifica cada leitura em normal / atenção / crítico / sem leitura.

Os limites são DIDÁTICOS/ILUSTRATIVOS, escolhidos para a demonstração. Não são
especificações de um veículo: cada fabricante e motor define os seus.
"""

# Para cada sensor: limites de atenção (warn) e crítico (crit), abaixo (low) ou acima (high).
# Sensores sem entrada aqui não têm limite e ficam sempre "normal".
THRESHOLDS = {
    "coolant_temperature": {"warn_high": 105, "crit_high": 115},
    "battery_voltage": {"crit_low": 12.0, "warn_low": 13.0, "warn_high": 14.8, "crit_high": 15.5},
    "rpm": {"warn_high": 5500, "crit_high": 6500},
    "short_term_fuel_trim": {"crit_low": -20, "warn_low": -10, "warn_high": 10, "crit_high": 20},
    "long_term_fuel_trim": {"crit_low": -20, "warn_low": -10, "warn_high": 10, "crit_high": 20},
}

STATUS_LABELS = {"normal": "Normal", "warn": "Atenção", "crit": "Crítico", "invalid": "Sem leitura"}
_ORDER = {"crit": 0, "invalid": 1, "warn": 2}

NOTICE = "Limites didáticos/ilustrativos, não especificações de um veículo."


def _fmt(number: float, unit: str) -> str:
    text = f"{number:g}".replace(".", ",")
    return f"{text} {unit}".strip()


def classify(key: str, value, unit: str = "") -> tuple[str, str | None]:
    """Retorna (status, explicação). A explicação é None quando o valor está normal."""
    if value is None:
        return "invalid", "Sinal inválido ou ausente"
    limits = THRESHOLDS.get(key, {})
    for level, name in (("crit", "crítico"), ("warn", "de atenção")):
        high = limits.get(f"{level}_high")
        low = limits.get(f"{level}_low")
        if high is not None and value >= high:
            return level, f"Acima do limite {name} ({_fmt(high, unit)})"
        if low is not None and value <= low:
            return level, f"Abaixo do limite {name} ({_fmt(low, unit)})"
    return "normal", None


def annotate(snapshot: dict) -> dict:
    """Acrescenta status a cada sensor e uma lista de alertas (mais graves primeiro)."""
    alerts = []
    for key, reading in snapshot["sensors"].items():
        status, note = classify(key, reading["value"], reading["unit"])
        reading["status"] = status
        reading["status_label"] = STATUS_LABELS[status]
        reading["status_note"] = note
        if status != "normal":
            alerts.append({"sensor": key, "status": status, "status_label": STATUS_LABELS[status],
                           "message": f"{reading['label']}: {note}."})
    alerts.sort(key=lambda a: _ORDER[a["status"]])
    snapshot["alerts"] = alerts
    snapshot["thresholds_notice"] = NOTICE
    return snapshot
