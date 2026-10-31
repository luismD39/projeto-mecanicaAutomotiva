-- Esquema do AutoScan Pro (ver DATA_MODEL.md). Idempotente: usa IF NOT EXISTS.

CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY,
    make TEXT NOT NULL,
    model TEXT NOT NULL,
    year INTEGER NOT NULL,
    engine TEXT,
    fuel_type TEXT NOT NULL,
    mileage_km REAL NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 0
);

-- Garante no próprio banco que só um veículo fique ativo por vez.
CREATE UNIQUE INDEX IF NOT EXISTS idx_vehicles_single_active
    ON vehicles (is_active) WHERE is_active = 1;

CREATE TABLE IF NOT EXISTS fault_codes (
    id INTEGER PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    system TEXT NOT NULL,
    explanation TEXT NOT NULL,
    causes_json TEXT NOT NULL,
    symptoms_json TEXT NOT NULL,
    checks_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS diagnostics (
    id INTEGER PRIMARY KEY,
    vehicle_id INTEGER NOT NULL REFERENCES vehicles (id),
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'simulation' CHECK (source = 'simulation'),
    status TEXT NOT NULL,
    summary TEXT NOT NULL,
    scenario_snapshot_json TEXT NOT NULL,
    sensor_snapshot_json TEXT NOT NULL,
    findings_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_diagnostics_vehicle ON diagnostics (vehicle_id, started_at);

CREATE TABLE IF NOT EXISTS diagnostic_faults (
    id INTEGER PRIMARY KEY,
    diagnostic_id INTEGER NOT NULL REFERENCES diagnostics (id) ON DELETE CASCADE,
    fault_code_id INTEGER NOT NULL REFERENCES fault_codes (id),
    status TEXT NOT NULL DEFAULT 'stored',
    evidence TEXT,
    UNIQUE (diagnostic_id, fault_code_id)
);

CREATE TABLE IF NOT EXISTS sensor_readings (
    id INTEGER PRIMARY KEY,
    diagnostic_id INTEGER REFERENCES diagnostics (id) ON DELETE CASCADE,
    sensor_key TEXT NOT NULL,
    display_name TEXT NOT NULL,
    value REAL,
    unit TEXT NOT NULL,
    recorded_at TEXT NOT NULL,
    validity TEXT NOT NULL DEFAULT 'valid'
);
