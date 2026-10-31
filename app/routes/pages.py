"""Páginas HTML da interface. A lista PAGES alimenta as rotas e a navegação lateral."""

import logging
import sqlite3

from flask import Blueprint, render_template

from app.db import get_db
from app.services import vehicles

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
     "summary": "Execute uma varredura OBD-II simulada no veículo ativo."},
    {"endpoint": "dados", "path": "/dados-em-tempo-real", "title": "Dados em tempo real", "icon": "activity",
     "phase": 5, "summary": "Acompanhe os parâmetros simulados do motor em cartões e gráficos."},
    {"endpoint": "diagnosticos", "path": "/diagnosticos", "title": "Diagnósticos", "icon": "clipboard", "phase": 7,
     "summary": "Detalhe do diagnóstico mais recente: DTCs, evidências, hipóteses e recomendações."},
    {"endpoint": "laboratorio", "path": "/laboratorio", "title": "Laboratório de falhas", "icon": "flask",
     "phase": 8, "summary": "Ative e desative cenários de falha para a demonstração."},
    {"endpoint": "historico", "path": "/historico", "title": "Histórico", "icon": "clock", "phase": 9,
     "summary": "Liste e filtre diagnósticos anteriores e baixe relatórios em PDF."},
    {"endpoint": "codigos", "path": "/codigos-dtc", "title": "Códigos DTC", "icon": "book", "phase": 6,
     "summary": "Pesquise códigos OBD-II, sintomas, possíveis causas e verificações."},
]


def _extra_context(endpoint: str) -> dict:
    if endpoint == "veiculos":
        return {"fuel_types": vehicles.FUEL_TYPES, "year_min": vehicles.YEAR_MIN,
                "year_max": vehicles.year_max(), "mileage_max": vehicles.MILEAGE_MAX_KM,
                "text_limits": vehicles.TEXT_LIMITS}
    return {}


def _make_view(page: dict):
    template = page.get("template", "pending.html")

    def view():
        return render_template(template, page=page, **_extra_context(page["endpoint"]))

    return view


for _page in PAGES:
    bp.add_url_rule(_page["path"], _page["endpoint"], _make_view(_page))


@bp.app_context_processor
def inject_layout():
    try:
        active_vehicle = vehicles.get_active_vehicle(get_db())
    except sqlite3.Error:
        # Sem o banco, a página ainda abre; o cabeçalho só não mostra o veículo.
        logger.exception("Falha ao consultar o veículo ativo")
        active_vehicle = None
    return {"pages": PAGES, "active_vehicle": active_vehicle}
