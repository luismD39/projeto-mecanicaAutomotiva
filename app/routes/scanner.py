"""Rotas do scanner, dos diagnósticos salvos e do relatório PDF. As regras ficam em app/services/."""

from flask import Blueprint, Response, current_app, jsonify, request

from app.db import get_db
from app.services import diagnostics, reports, scanner

bp = Blueprint("scanner", __name__, url_prefix="/api")


@bp.post("/scanner/start")
def start():
    return jsonify(scanner.start_scan(get_db(), current_app.extensions["ecu"])), 201


@bp.get("/diagnostics")
def list_diagnostics():
    db = get_db()
    filters = diagnostics.parse_filters(db, request.args)
    return jsonify({"diagnostics": diagnostics.list_diagnostics(db, filters),
                    "limit": diagnostics.LIST_LIMIT})


@bp.get("/reports/<int:diagnostic_id>/pdf")
def report_pdf(diagnostic_id: int):
    pdf = reports.build_pdf(scanner.get_diagnostic(get_db(), diagnostic_id))
    return Response(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="autoscan-diagnostico-{diagnostic_id}.pdf"',
    })


@bp.get("/diagnostics/<int:diagnostic_id>")
def detail(diagnostic_id: int):
    return jsonify(scanner.get_diagnostic(get_db(), diagnostic_id))
