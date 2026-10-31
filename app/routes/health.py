"""Rota de saúde: confirma que a API e o banco respondem."""

from datetime import datetime, timezone

from flask import Blueprint, jsonify

from app.config import APP_NAME, APP_VERSION
from app.db import get_db

bp = Blueprint("health", __name__, url_prefix="/api")


@bp.get("/health")
def health():
    get_db().execute("SELECT 1").fetchone()
    return jsonify(
        {
            "status": "ok",
            "app": APP_NAME,
            "version": APP_VERSION,
            "database": "ok",
            "source": "simulation",
            "message": "Simulação didática: não há conexão com veículo real.",
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
