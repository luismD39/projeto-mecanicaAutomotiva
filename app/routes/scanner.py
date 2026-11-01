"""Rotas do scanner e dos diagnósticos salvos. As regras ficam em app/services/scanner.py."""

from flask import Blueprint, current_app, jsonify

from app.db import get_db
from app.services import scanner

bp = Blueprint("scanner", __name__, url_prefix="/api")


@bp.post("/scanner/start")
def start():
    return jsonify(scanner.start_scan(get_db(), current_app.extensions["ecu"])), 201


@bp.get("/diagnostics/<int:diagnostic_id>")
def detail(diagnostic_id: int):
    return jsonify(scanner.get_diagnostic(get_db(), diagnostic_id))
