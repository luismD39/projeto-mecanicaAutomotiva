"""Consultas de diagnósticos salvos. A varredura que cria diagnósticos chega na Fase 6."""

import sqlite3


def get_latest(db: sqlite3.Connection, vehicle_id: int) -> dict | None:
    row = db.execute(
        """
        SELECT d.id, d.completed_at, d.status, d.summary,
               (SELECT COUNT(*) FROM diagnostic_faults f WHERE f.diagnostic_id = d.id) AS dtc_count
        FROM diagnostics d
        WHERE d.vehicle_id = ?
        ORDER BY d.completed_at DESC, d.id DESC
        LIMIT 1
        """,
        (vehicle_id,),
    ).fetchone()
    return dict(row) if row else None
