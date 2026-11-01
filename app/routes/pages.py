"""Páginas HTML da interface. A lista PAGES alimenta as rotas e a navegação lateral."""

import logging
import sqlite3
from datetime import datetime

from flask import Blueprint, current_app, render_template, request

from app.db import get_db
from app.services import diagnostics, sensor_status, simulator, vehicles

logger = logging.getLogger(__name__)

bp = Blueprint("pages", __name__)

# "phase" indica em qual fase do DEVELOPMENT_PLAN.md a tela ganha funcionalidade.
# "template" existe nas telas já implementadas; as demais usam pending.html.
PAGES = [
    {"endpoint": "dashboard", "path": "/", "title": "Dashboard", "icon": "dashboard", "phase": 5,
     "template": "dashboard.html",
     "summary": "Visão geral do veículo ativo, da ECU simulada e do último diagnóstico."},
    {"endpoint": "veiculos", "path": "/veiculos", "title": "Veículos", "icon": "car", "phase": 3,
     "template": "vehicles.html",
     "summary": "Cadastre, edite e selecione o veículo fictício usado nas simulações."},
    {"endpoint": "scanner", "path": "/scanner", "title": "Scanner", "icon": "scan", "phase": 6,
     "template": "scanner.html",
     "summary": "Execute uma varredura OBD-II simulada no veículo ativo."},
    {"endpoint": "dados", "path": "/dados-em-tempo-real", "title": "Dados em tempo real", "icon": "activity",
     "phase": 5, "template": "live.html",
     "summary": "Acompanhe os parâmetros simulados do motor em cartões e gráficos."},
    {"endpoint": "diagnosticos", "path": "/diagnosticos", "title": "Diagnósticos", "icon": "clipboard", "phase": 7,
     "template": "diagnostics.html",
     "summary": "Detalhe do diagnóstico mais recente: DTCs, evidências, hipóteses e recomendações."},
    {"endpoint": "laboratorio", "path": "/laboratorio", "title": "Laboratório de falhas", "icon": "flask",
     "phase": 8, "template": "lab.html",
     "summary": "Ative e desative cenários de falha para a demonstração."},
    {"endpoint": "historico", "path": "/historico", "title": "Histórico", "icon": "clock", "phase": 9,
     "summary": "Liste e filtre diagnósticos anteriores e baixe relatórios em PDF."},
    {"endpoint": "codigos", "path": "/codigos-dtc", "title": "Códigos DTC", "icon": "book", "phase": 6,
     "template": "codes.html",
     "summary": "Pesquise códigos OBD-II, sintomas, possíveis causas e verificações."},
]


# Sensores exibidos em destaque no Dashboard, com rótulo curto.
DASHBOARD_SENSORS = [
    ("rpm", "Rotação (RPM)"),
    ("coolant_temperature", "Temperatura (ECT)"),
    ("vehicle_speed", "Velocidade (VSS)"),
    ("engine_load", "Carga do motor"),
    ("throttle_position", "Borboleta (TPS)"),
    ("battery_voltage", "Tensão do módulo"),
]

# Sensores que mais mudam com os cenários de falha, mostrados no Laboratório.
LAB_SENSORS = [
    ("coolant_temperature", "Temperatura (ECT)"),
    ("battery_voltage", "Tensão do módulo"),
    ("rpm", "Rotação (RPM)"),
    ("vehicle_speed", "Velocidade (VSS)"),
    ("long_term_fuel_trim", "Correção longo prazo (LTFT)"),
]


def _extra_context(endpoint: str) -> dict:
    if endpoint == "veiculos":
        return {"fuel_types": vehicles.FUEL_TYPES, "year_min": vehicles.YEAR_MIN,
                "year_max": vehicles.year_max(), "mileage_max": vehicles.MILEAGE_MAX_KM,
                "text_limits": vehicles.TEXT_LIMITS}
    if endpoint == "dashboard":
        db = get_db()
        active = vehicles.get_active_vehicle(db)
        return {"sensors": simulator.SENSORS, "dashboard_sensors": DASHBOARD_SENSORS,
                "last_diagnostic": diagnostics.get_latest(db, active["id"]) if active else None,
                "thresholds_notice": sensor_status.NOTICE}
    if endpoint == "diagnosticos":
        # ?id=N abre um diagnóstico específico; sem id, o mais recente. O JS consulta a API e trata 404.
        return {"diagnostic_id": request.args.get("id", type=int) or diagnostics.get_latest_id(get_db())}
    if endpoint == "laboratorio":
        return {"ecu_status": current_app.extensions["ecu"].status(), "sensors": simulator.SENSORS,
                "scenario_names": {sid: s["name"] for sid, s in simulator.SCENARIOS.items()},
                "lab_sensors": LAB_SENSORS, "thresholds_notice": sensor_status.NOTICE}
    if endpoint == "dados":
        return {"sensors": simulator.SENSORS, "modes": simulator.MODES,
                "thresholds_notice": sensor_status.NOTICE}
    return {}


def _make_view(page: dict):
    template = page.get("template", "pending.html")

    def view():
        return render_template(template, page=page, **_extra_context(page["endpoint"]))

    return view


for _page in PAGES:
    bp.add_url_rule(_page["path"], _page["endpoint"], _make_view(_page))


@bp.app_template_filter("datetime_br")
def datetime_br(iso: str) -> str:
    """'2026-10-31T21:04:05+00:00' -> '31/10/2026 18:04' (horário local do computador)."""
    try:
        return datetime.fromisoformat(iso).astimezone().strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError):
        return iso


@bp.app_context_processor
def inject_layout():
    try:
        active_vehicle = vehicles.get_active_vehicle(get_db())
    except sqlite3.Error:
        # Sem o banco, a página ainda abre; o cabeçalho só não mostra o veículo.
        logger.exception("Falha ao consultar o veículo ativo")
        active_vehicle = None
    return {"pages": PAGES, "active_vehicle": active_vehicle}
