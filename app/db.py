"""Acesso ao banco SQLite: uma conexão por requisição, com chaves estrangeiras ligadas."""

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def connect(database: str) -> sqlite3.Connection:
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    # O SQLite vem com chaves estrangeiras desligadas por padrão; precisa ligar a cada conexão.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(database: str) -> None:
    """Cria as tabelas que ainda não existem. Pode ser chamada várias vezes."""
    Path(database).parent.mkdir(parents=True, exist_ok=True)
    with connect(database) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.close()
