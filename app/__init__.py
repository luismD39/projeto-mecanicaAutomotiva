"""AutoScan Pro: simulador didático de diagnóstico automotivo."""

import logging
from contextlib import closing

from flask import Flask

from app import db
from app.config import Config
from app.errors import register_error_handlers
from app.icons import icon
from app.routes import catalog, health, pages, scanner, simulator, vehicles
from app.security import register_security
from app.services import fault_codes
from app.services.simulator import EcuSimulator


def create_app(overrides: dict | None = None) -> Flask:
    app = Flask(__name__)
    app.json.ensure_ascii = False  # acentos legíveis no JSON
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    db.init_db(app.config["DATABASE"])
    with closing(db.connect(app.config["DATABASE"])) as conn:
        fault_codes.seed(conn)
    app.teardown_appcontext(db.close_db)

    # Uma ECU simulada por aplicação; o estado fica em memória (reinicia junto com o servidor).
    app.extensions["ecu"] = EcuSimulator(seed=app.config.get("SIMULATOR_SEED"))

    register_error_handlers(app)
    register_security(app)
    app.jinja_env.globals["icon"] = icon
    app.register_blueprint(health.bp)
    app.register_blueprint(pages.bp)
    app.register_blueprint(vehicles.bp)
    app.register_blueprint(simulator.bp)
    app.register_blueprint(catalog.bp)
    app.register_blueprint(scanner.bp)
    return app
