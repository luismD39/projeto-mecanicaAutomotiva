"""Rotas /api/vehicles. As regras ficam em app/services/vehicles.py."""

from flask import Blueprint, jsonify, request

from app.db import get_db
from app.services import vehicles

bp = Blueprint("vehicles", __name__, url_prefix="/api/vehicles")


@bp.get("")
def list_vehicles():
    return jsonify({"vehicles": vehicles.list_vehicles(get_db())})


@bp.post("")
def create_vehicle():
    return jsonify(vehicles.create_vehicle(get_db(), request.get_json(silent=True))), 201


@bp.post("/demo")
def create_demo_vehicles():
    created = vehicles.create_demo_vehicles(get_db())
    return jsonify({"created": len(created), "vehicles": vehicles.list_vehicles(get_db())}), 201


@bp.get("/<int:vehicle_id>")
def get_vehicle(vehicle_id: int):
    return jsonify(vehicles.get_vehicle(get_db(), vehicle_id))


@bp.put("/<int:vehicle_id>")
def update_vehicle(vehicle_id: int):
    return jsonify(vehicles.update_vehicle(get_db(), vehicle_id, request.get_json(silent=True)))


@bp.delete("/<int:vehicle_id>")
def delete_vehicle(vehicle_id: int):
    vehicles.delete_vehicle(get_db(), vehicle_id)
    return "", 204


@bp.post("/<int:vehicle_id>/activate")
def activate_vehicle(vehicle_id: int):
    return jsonify(vehicles.activate_vehicle(get_db(), vehicle_id))
