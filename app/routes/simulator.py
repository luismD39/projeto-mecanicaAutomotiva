"""Rotas da ECU simulada. As regras ficam em app/services/simulator.py."""

from flask import Blueprint, current_app, jsonify, request

from app.services import sensor_status
from app.services.errors import ValidationError

bp = Blueprint("simulator", __name__, url_prefix="/api")


def _ecu():
    return current_app.extensions["ecu"]


@bp.get("/sensors/live")
def live():
    return jsonify(sensor_status.annotate(_ecu().snapshot()))


@bp.post("/simulator/mode")
def set_mode():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("Envie o modo em formato JSON, por exemplo {\"mode\": \"idle\"}.")
    return jsonify(_ecu().set_mode(data.get("mode")))


@bp.get("/simulator/scenarios")
def scenarios():
    return jsonify(_ecu().status())


@bp.post("/simulator/scenarios/<scenario_id>/activate")
def activate(scenario_id: str):
    return jsonify(_ecu().activate(scenario_id))


@bp.post("/simulator/scenarios/<scenario_id>/deactivate")
def deactivate(scenario_id: str):
    return jsonify(_ecu().deactivate(scenario_id))


@bp.post("/simulator/reset")
def reset():
    return jsonify(_ecu().reset())
