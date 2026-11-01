"""Rotas do catálogo de códigos DTC. As regras ficam em app/services/fault_codes.py."""

from flask import Blueprint, jsonify, request

from app.db import get_db
from app.services import fault_codes

bp = Blueprint("catalog", __name__, url_prefix="/api/fault-codes")


@bp.get("")
def search():
    return jsonify({"fault_codes": fault_codes.search(get_db(), request.args.get("q", "")),
                    "note": fault_codes.NOTE})


@bp.get("/<code>")
def detail(code: str):
    return jsonify(fault_codes.get_fault_code(get_db(), code))
